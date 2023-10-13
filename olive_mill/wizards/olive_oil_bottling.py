# Copyright 2018-2023 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, _
from odoo.tools import float_compare, float_is_zero, float_round
from odoo.exceptions import UserError

OIL_QTY_NOT_EMPTY = 0.1


class OliveOilBottling(models.TransientModel):
    _name = 'olive.oil.bottling'
    _description = 'Wizard to fill-up olive oil bottles'
    _check_company_auto = True

    # START first 1st step (select)
    company_id = fields.Many2one(
        'res.company', ondelete='cascade', required=True,
        default=lambda self: self.env.company)
    bottle_product_id = fields.Many2one(
        'product.product', string='Oil Bottle to Produce',
        domain=[('detailed_type', '=', 'olive_bottle_full')], required=True,
        readonly=True, states={'select': [('readonly', False)]})
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse', required=True, check_company=True,
        domain="[('olive_mill', '=', True), ('company_id', '=', company_id)]",
        default=lambda self: self.env.user._default_olive_mill_wh(),
        readonly=True, states={'select': [('readonly', False)]})
    season_id = fields.Many2one(
        'olive.season', string='Season', required=True, check_company=True,
        domain="[('company_id', '=', company_id)]",
        default=lambda self: self.env.company.current_season_id.id,
        readonly=True, states={'select': [('readonly', False)]})

    # START fields 2nd step (qty)
    bottle_volume = fields.Float(
        string='Bottle Volume',
        digits='Product Unit of Measure', readonly=True)
    oil_product_id = fields.Many2one(
        'product.product', string='Oil Type', readonly=True)
    bom_id = fields.Many2one(
        'mrp.bom', string='Bill of Material', readonly=True)
    bottle_qty = fields.Integer(
        string='Produced Bottles Qty',
        readonly=True, states={'qty': [('readonly', False)]})
    src_location_id = fields.Many2one(
        'stock.location', string='Oil Tank', check_company=True,
        domain="[('olive_tank_type', '!=', False), ('usage', '=', 'internal'), ('oil_product_id', '=', oil_product_id), ('olive_season_id', '=', season_id), ('company_id', '=', company_id)]",
        readonly=True, states={'qty': [('readonly', False)]})
    src_location_end_status = fields.Selection([
        ('empty', 'Empty Tank'),
        ('not_empty', 'Tank not Empty'),
        ], default='not_empty', string='Oil Tank Status at End of Bottling',
        readonly=True, states={'qty': [('readonly', False)]})
    other_src_location_id = fields.Many2one(
        'stock.location', string='Source Location for Empty Bottles',
        domain="[('olive_tank_type', '=', False), ('usage', '=', 'internal'), ('company_id', '=', company_id)]",
        readonly=True, states={'qty': [('readonly', False)]}, check_company=True)
    dest_location_id = fields.Many2one(
        'stock.location', string='Destination Location for Full Bottles',
        domain="[('olive_tank_type', '=', False), ('usage', '=', 'internal'), ('company_id', '=', company_id)]",
        readonly=True, states={'qty': [('readonly', False)]}, check_company=True)

    # Start fields last step (produce)
    src_location_start_qty = fields.Float(
        string='Oil Qty in Tank before Bottling',
        digits='Product Unit of Measure', readonly=True)
    oil_qty = fields.Float(
        string='Oil Qty for Bottling',
        digits='Product Unit of Measure', readonly=True)
    src_location_end_qty = fields.Float(
        string='Oil Qty in Tank after Bottling',
        digits='Product Unit of Measure', readonly=True,
        help="This field doesn't take into account the inventory operation")
    inventory_required = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
        ], readonly=True, string='Inventory Required')
    inventory_start_qty = fields.Float(
        string='Inventory Oil Qty in Tank before Bottling',
        digits='Product Unit of Measure', readonly=True)
    inventory_end_qty = fields.Float(
        string='Inventory Oil Qty in Tank after Bottling',
        digits='Product Unit of Measure', readonly=True)
    expiry_date = fields.Date(string='Expiry Date')
    lot_type = fields.Selection([
        ('new', 'New'),
        ('existing', 'Existing'),
        ], string='Lot Type', default='new')
    lot_name = fields.Char(string='Lot')
    lot_id = fields.Many2one(
        'stock.production.lot', string='Existing Lot',
        domain="[('company_id', '=', company_id), ('product_id', '=', bottle_product_id), ('expiry_date', '=', expiry_date)]", check_company=True)
    state = fields.Selection([
        ('select', 'Select Oil Bottle'),
        ('qty', 'Enter Quantity'),
        ('produce', 'Produce'),
        ], default='select', readonly=True)

    def select2qty(self):
        self.ensure_one()
        assert self.state == 'select'
        bom, oil_product_id, bottle_volume = self.bottle_product_id.oil_bottle_full_get_bom_and_oil_product()
        assert oil_product_id.detailed_type == 'olive_oil'
        self.write({
            'state': 'qty',
            'bom_id': bom.id,
            'oil_product_id': oil_product_id.id,
            'bottle_volume': bottle_volume,
            'dest_location_id': self.warehouse_id.lot_stock_id.id,
            'other_src_location_id': self.warehouse_id.lot_stock_id.id,
            'expiry_date': self.season_id.default_expiry_date,
            })
        action = self.env['ir.actions.actions']._for_xml_id('olive_mill.olive_oil_bottling_action')
        action['res_id'] = self.id
        return action

    def qty2produce(self):
        self.ensure_one()
        assert self.state == 'qty'
        prec = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        if self.bottle_qty <= 0:
            raise UserError(_(
                "The quantity of bottles to produce must be positive."))
        src_location_start_qty = self.src_location_id.olive_oil_tank_check(merge_if_not_merged=True)
        # Check we have enough oil
        oil_qty = self.bottle_qty * self.bottle_volume
        src_location_end_qty = float_round(src_location_start_qty - oil_qty, precision_digits=prec)
        inventory_required = 'no'
        inventory_start_qty = inventory_end_qty = 0
        fcompare = float_compare(src_location_start_qty, oil_qty, precision_digits=prec)
        if fcompare < 0:
            if self.src_location_end_status == 'empty':
                inventory_required = 'yes'
                inventory_start_qty = oil_qty
                inventory_end_qty = 0
            elif self.src_location_end_status == 'not_empty':
                inventory_required = 'yes'
                inventory_start_qty = oil_qty + OIL_QTY_NOT_EMPTY
                inventory_end_qty = OIL_QTY_NOT_EMPTY
        elif fcompare == 0:
            if self.src_location_end_status == 'not_empty':
                inventory_required = 'yes'
                inventory_start_qty = oil_qty + OIL_QTY_NOT_EMPTY
                inventory_end_qty = OIL_QTY_NOT_EMPTY
        elif fcompare > 0:
            if self.src_location_end_status == 'empty':
                inventory_required = 'yes'
                inventory_start_qty = oil_qty
                inventory_end_qty = 0

        self.write({
            'state': 'produce',
            'src_location_start_qty': src_location_start_qty,
            'src_location_end_qty': src_location_end_qty,
            'oil_qty': oil_qty,
            'inventory_required': inventory_required,
            'inventory_start_qty': inventory_start_qty,
            'inventory_end_qty': inventory_end_qty,
            })
        action = self.env['ir.actions.actions']._for_xml_id('olive_mill.olive_oil_bottling_action')
        action['res_id'] = self.id
        return action

    def validate(self):
        self.ensure_one()
        assert self.state == 'produce'
        prec = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        origin = _('Olive oil bottling wizard')
        mpo = self.env['mrp.production']
        splo = self.env['stock.production.lot']
        sqo = self.env['stock.quant']
        smo = self.env['stock.move']
        mblo = self.env['mrp.bom.line']
        oil_product = self.oil_product_id
        bottle_product = self.bottle_product_id
        bom = self.bom_id
        assert self.bottle_qty > 0
        assert self.src_location_id
        assert self.other_src_location_id
        assert self.dest_location_id
        assert self.expiry_date
        assert self.lot_type
        assert oil_product.tracking == 'lot'
        assert bottle_product.tracking == 'lot'
        assert self.inventory_required in ('yes', 'no')
        if self.lot_type == 'new' and self.expiry_date < fields.Date.context_today(self):
            raise UserError(_(
                "The expiry date should not be in the past."))
        # Re-check the qty of oil in tank (could have been changed after validation
        # of last step
        src_location_start_qty = self.src_location_id.olive_oil_tank_check(merge_if_not_merged=True)
        # raise_if_not_merged=True by default, so merge check is done here
        if float_compare(src_location_start_qty, self.src_location_start_qty, precision_digits=prec):
            raise UserError(_(
                "The quantity of oil in tank has changed between the "
                "last step of the wizard (%s L) and now (%s L). You "
                "must cancel the wizard and start again.") % (
                    self.src_location_start_qty, src_location_start_qty))
        # Check we have enough empty bottles
        other_product_bom_lines = mblo.search([
            ('bom_id', '=', bom.id),
            ('product_id', '!=', oil_product.id)])
        for bom_line in other_product_bom_lines.filtered(lambda x: x.product_id.type == 'product'):
            product = bom_line.product_id
            qty_required = self.bottle_qty * bom_line.product_qty
            free_start_qty = product.with_context(location=self.other_src_location_id.id).free_qty
            uom = product.uom_id
            if float_compare(free_start_qty, qty_required, precision_digits=0) <= 0:
                raise UserError(_(
                    "The stock location '%s' contains %s %s '%s' without reservation. "
                    "This is not enough for this bottling (%s %s required).") % (
                        self.other_src_location_id.display_name,
                        free_start_qty, uom.name, product.display_name,
                        qty_required, uom.name))
        # Inventory
        if self.inventory_required == 'yes':
            tank_quants = sqo.search([('location_id', '=', self.src_location_id.id)])
            assert len(tank_quants) == 1
            assert tank_quants.product_id == oil_product
            assert tank_quants.lot_id
            oil_lot_id = tank_quants.lot_id.id
            inv_line_vals = {
                'product_id': oil_product.id,
                'product_uom_id': oil_product.uom_id.id,
                'location_id': self.src_location_id.id,
                'prod_lot_id': oil_lot_id,
                'product_qty': self.inventory_start_qty,
                'theoretical_qty': src_location_start_qty,
                }
            inventory = self.env['stock.inventory'].create({
                'name': _('Oil bottling %s from %s') % (self.bottle_product_id.name, self.src_location_id.name),
                'location_ids': [(6, 0, [self.src_location_id.id])],
                'product_ids': [(6, 0, [oil_product.id])],
                'line_ids': [(0, 0, inv_line_vals)],
                })
            inventory.action_start()  # it won't create inventory lines because there is already a line
            inventory.action_validate()
            src_location_start_qty = self.src_location_id.olive_oil_tank_check()
            if float_compare(src_location_start_qty, self.inventory_start_qty, precision_digits=prec):
                raise UserError(_(
                    "Something went wrong in the automatic inventory operation."))

        # Get/Create finished lot
        if self.lot_type == 'new':
            existing_lots = splo.search([
                ('product_id', '=', bottle_product.id),
                ('name', '=', self.lot_name)])
            if existing_lots:
                raise UserError(_(
                    "Lot '%s' already exists for the same product '%s'.")
                    % (self.lot_name, bottle_product.display_name))
            bottle_lot = splo.create({
                'product_id': bottle_product.id,
                'name': self.lot_name,
                'expiry_date': self.expiry_date,
                })
        else:
            bottle_lot = self.lot_id
            if not bottle_lot:
                raise UserError(_(
                    'You must select an existing lot for the bottle product.'))

        mo = mpo.create({
            'product_id': bottle_product.id,
            'product_qty': self.bottle_qty,
            'product_uom_id': bottle_product.uom_id.id,
            'location_src_id': self.src_location_id.id,
            'location_dest_id': self.dest_location_id.id,
            'origin': origin,
            'bom_id': bom.id,
            'picking_type_id': self.warehouse_id.manu_type_id.id,
            'company_id': self.company_id.id,
        })
        smo.create(mo._get_moves_raw_values())
        smo.create(mo._get_moves_finished_values())
        oil_raw_move = smo.search([
            ('product_id.detailed_type', '=', 'olive_oil'),
            ('raw_material_production_id', '=', mo.id)])
        other_raw_moves = smo.search([
            ('product_id.detailed_type', '!=', 'olive_oil'),
            ('raw_material_production_id', '=', mo.id)])
        # BOM has already been checked, so this should really never happen
        assert len(oil_raw_move) == 1, 'Wrong number of oil raw moves'
        # HACK change source location for other raw moves
        other_raw_moves.write({'location_id': self.other_src_location_id.id})
        assert mo.state == 'draft'
        mo.action_confirm()
        assert mo.state == 'confirmed'
        mo.write({
            'qty_producing': self.bottle_qty,
            'lot_producing_id': bottle_lot.id,
            })
        assert len(mo.move_raw_ids) > 0, 'Missing raw moves'
        assert len(mo.move_finished_ids) == 1, 'Wrong finished moves'
        assert mo.move_finished_ids[0].product_id == bottle_product, 'Wrong product on finished move'
        for rmove in other_raw_moves:
            if rmove.product_id.tracking in ('lot', 'serial'):
                raise UserError(_(
                    "The bill of material has the component '%s' "
                    "which is tracked by lot or serial. For the moment, "
                    "the only supported scenario is where the only component "
                    "of the bill of material tracked by lot is the oil.")
                    % rmove.product_id.display_name)
        assert mo.state == 'to_close'
        mo.action_assign()
        if mo.components_availability_state != 'available':
            raise UserError(_(
                "Could not reserve the raw material for this bottling operation. "
                "Check that you have enough oil and empty bottles."))
        for raw_move in mo.move_raw_ids:
            for ml in raw_move.move_line_ids:
                if ml.product_id.detailed_type == 'olive_oil':
                    assert ml.lot_id
                assert ml.product_uom_qty > 0
                ml.write({'qty_done': ml.product_uom_qty})
        mo.button_mark_done()

        # Check oil end qty
        oil_end_qty_in_tank = self.src_location_id.olive_oil_tank_check(raise_if_empty=False)
        if float_compare(
                oil_end_qty_in_tank,
                src_location_start_qty - self.bottle_qty * self.bottle_volume,
                precision_digits=prec):
            raise UserError(_(
                "The end quantity in tank (%s L) is wrong. This should never happen.")
                % oil_end_qty_in_tank)
        if (
                self.src_location_end_status == 'empty_tank' and
                not float_is_zero(oil_end_qty_in_tank, precision_digits=prec)):
            raise UserError(_(
                "The end quantity in tank (%s L) is wrong. It should be 0.") % oil_end_qty_in_tank)

        action = self.env['ir.actions.actions']._for_xml_id('mrp.mrp_production_action')
        action.update({
            'res_id': mo.id,
            'views': False,
            'view_mode': 'form,tree,kanban,calendar',
            })
        return action
