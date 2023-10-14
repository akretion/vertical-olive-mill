# Copyright 2018-2023 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.tools import float_compare
from odoo.exceptions import UserError


class OliveOilPicking(models.TransientModel):
    _name = 'olive.oil.picking'
    _description = 'Wizard to ship loose olive oil'

    move_id = fields.Many2one(
        'stock.move', string='Stock Move', readonly=True, required=True)
    picking_id = fields.Many2one(related='move_id.picking_id')
    company_id = fields.Many2one(related='move_id.company_id')
    oil_product_id = fields.Many2one(
        'product.product', string='Oil Type', readonly=True)
    oil_qty = fields.Float(
        string='Oil Qty', readonly=True,
        digits='Product Unit of Measure')
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse',
        domain=[('olive_mill', '=', True)],
        default=lambda self: self.env.user._default_olive_mill_wh())
    src_location_id = fields.Many2one(
        'stock.location', string='Olive Tank', required=True)
    dest_location_id = fields.Many2one(
        'stock.location', string='Destination Location',
        readonly=True, required=True)
    container_src_location_id = fields.Many2one(
        'stock.location', string='Source Location for Empty Containers',
        domain=[('usage', '=', 'internal')])
    container_ids = fields.One2many(
        'olive.oil.picking.container', 'wizard_id', 'Containers Used')

    @api.onchange('warehouse_id')
    def warehouse_id_change(self):
        if self.warehouse_id:
            self.container_src_location_id = self.warehouse_id.lot_stock_id

    def validate(self):
        self.ensure_one()
        assert self.move_id
        pr_oil = self.env['decimal.precision'].precision_get(
            'Olive Oil Volume')
        pr_prod = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')
        origin = _('Ship loose oil wizard')
        if self.picking_id:
            origin = _(
                'Ship loose oil from picking %s') % self.picking_id.name
        spo = self.env['stock.picking']
        smo = self.env['stock.move']
        oil_product = self.oil_product_id
        if self.move_id.state != 'confirmed':
            state2label = dict(self.move_id.fields_get('state', 'selection')['state']['selection'])
            raise UserError(_(
                "The stock move '%s' ID %d is in %s state. This wizard "
                "is designed to work only when the move is in confirmed "
                "state.") % (
                    self.move_id.display_name,
                    self.move_id.id,
                    state2label[self.move_id.state]))
        if float_compare(self.oil_qty, 0, precision_digits=pr_prod) <= 0:
            raise UserError(_(
                "The quantity of olive oil must be positive."))
        assert self.src_location_id
        assert self.dest_location_id
        assert self.container_src_location_id
        assert oil_product.tracking == 'lot'
        oil_start_qty_in_tank = self.src_location_id.olive_oil_tank_check(
            merge_if_not_merged=True, raise_if_empty=True)
        # Check we have enough oil
        if float_compare(
                oil_start_qty_in_tank, self.oil_qty,
                precision_digits=pr_oil) <= 0:
            raise UserError(_(
                "The tank %s currently contains %s liters. This is not "
                "enough for this operation (%s liters required).") % (
                    self.src_location_id.name,
                    oil_start_qty_in_tank,
                    self.oil_qty))
        # Check we have enough containers
        if self.container_ids:
            if not self.container_src_location_id:
                raise UserError(_(
                    "You must select a source location for empty containers."))
        for cline in self.container_ids:
            if cline.product_id.type != 'product':
                continue
            free_start_qty = cline.with_context(location=self.container_src_location_id.id).product_id.free_qty
            uom = cline.product_id.uom_id
            if float_compare(
                    free_start_qty, cline.qty, precision_digits=0) <= 0:
                raise UserError(_(
                    "The stock location '%s' contains %s %s '%s' without "
                    "reservation. This is not enough to prepare this loose "
                    "olive oil (%s %s required).") % (
                        self.container_src_location_id.display_name,
                        free_start_qty, uom.name, cline.product_id.name,
                        cline.qty, uom.name))
        if not self.warehouse_id.int_type_id:
            raise UserError(_(
                'Internal picking type not configured on warehouse %s.')
                % self.warehouse_id.display_name)
        # Move oil
        assert self.oil_product_id == self.src_location_id.oil_product_id
        opickings = self.src_location_id.olive_oil_transfer(
            self.dest_location_id, 'partial', self.warehouse_id,
            partial_transfer_qty=self.oil_qty, origin=origin)
        oil_lot = opickings[0].move_line_ids[0].lot_id
        assert self.oil_product_id == opickings[0].move_lines[0].product_id
        # Move containers too
        # TODO don't test !=, test "is not child_of"
        if (
                self.container_ids and
                self.container_src_location_id != self.dest_location_id):
            cpicking = spo.create({
                'company_id': self.company_id.id,
                'picking_type_id': self.warehouse_id.int_type_id.id,
                'origin': origin,
                'move_type': 'one',
                'location_id': self.container_src_location_id.id,
                'location_dest_id': self.dest_location_id.id,
                })
            for cline in self.container_ids:
                if (
                        cline.product_id.tracking and
                        cline.product_id.tracking != 'none'):
                    raise UserError(_(
                        "Only containers that are not tracked by lots or "
                        "serial are accepted in this wizard. The container "
                        "'%s' is tracked by lot or serial.")
                        % cline.product_id.display_name)
                name = _(
                    'Container to prepare loose olive oil: '
                    '%s') % cline.product_id.name
                cmove = smo.create({
                    'company_id': self.company_id.id,
                    'picking_id': cpicking.id,
                    'product_id': cline.product_id.id,
                    'product_uom': cline.product_id.uom_id.id,
                    'location_id': self.container_src_location_id.id,
                    'location_dest_id': self.dest_location_id.id,
                    'product_uom_qty': cline.qty,
                    'name': name,
                    'origin': origin,
                    'move_line_ids': [(0, 0, {
                        'picking_id': cpicking.id,
                        'product_id': cline.product_id.id,
                        'product_uom_id': cline.product_id.uom_id.id,
                        'location_id': self.container_src_location_id.id,
                        'location_dest_id': self.dest_location_id.id,
                        'qty_done': cline.qty,
                        })],
                    })
                cmove._action_done()
                assert cmove.state == 'done'

        # Check oil end qty
        oil_end_qty_in_tank = self.src_location_id.olive_oil_tank_check(raise_if_empty=False)
        if float_compare(
                oil_end_qty_in_tank, oil_start_qty_in_tank - self.oil_qty,
                precision_digits=pr_oil):
            raise UserError(_(
                "The end quantity in tank (%s L) is wrong. This should never "
                "happen.") % oil_end_qty_in_tank)

        # Add containers to picking
        # TODO if, in the same picking, 2 withdrawals with container on same location
        if self.container_ids and self.picking_id:
            for cline in self.container_ids:
                name = _(
                    'Container for loose olive oil: '
                    '%s') % cline.product_id.name
                smo.create({
                    'company_id': self.company_id.id,
                    'picking_id': self.picking_id.id,
                    'product_id': cline.product_id.id,
                    'product_uom': cline.product_id.uom_id.id,
                    'location_id': self.dest_location_id.id,
                    'location_dest_id': self.picking_id.location_dest_id.id,
                    'product_uom_qty': cline.qty,
                    'name': name,
                    'origin': origin,
                    })

        # Oil : assign to move
        action = True
        if self.move_id.move_line_ids:
            raise UserError(_(
                "The stock move with product '%s' already has detailed "
                "operations. It is certainly due to the fact that "
                "there was some unreserved oil left on stock "
                "location '%s', which is probably caused by a "
                "previous execution of this wizard on a picking that "
                "was later cancelled.") % (
                    self.move_id.product_id.display_name,
                    self.move_id.location_id.display_name))
        assert self.move_id.product_id.id == self.oil_product_id.id
        assert self.move_id.product_uom.id == self.oil_product_id.uom_id.id
        self.env['stock.move.line'].create({
            'picking_id': self.picking_id.id,
            'move_id': self.move_id.id,
            'product_id': self.oil_product_id.id,
            'product_uom_id': self.oil_product_id.uom_id.id,
            'location_id': self.move_id.location_id.id,
            'location_dest_id': self.move_id.location_dest_id.id,
            'qty_done': self.oil_qty,
            'lot_id': oil_lot.id,
            })
        if self.picking_id:
            self.picking_id.action_assign()
            cmlines = self.env['stock.move.line'].search([
                ('picking_id', '=', self.picking_id.id),
                ('product_id.detailed_type', '=', 'olive_bottle_empty'),
                ('state', 'not in', ('done', 'cancel')),
                ])
            for cmline in cmlines:
                cmline.write({'qty_done': cmline.product_qty})
            if self.picking_id.olive_oil_picking_wizard_next_move_id:
                action = self.picking_id.start_olive_oil_picking_wizard()
        return action


class OliveOilPickingContainer(models.TransientModel):
    _name = 'olive.oil.picking.container'
    _description = 'Loose Olive Oil: Container Lines'

    wizard_id = fields.Many2one('olive.oil.picking', ondelete='cascade')
    product_id = fields.Many2one(
        'product.product', string='Container',
        required=True, ondelete='restrict',
        domain=[
            ('detailed_type', '=', 'olive_bottle_empty'),
            ('tracking', 'not in', ('lot', 'serial'))])
    qty = fields.Float(
        string='Quantity', default=1,
        digits='Product Unit of Measure', required=True)
    uom_id = fields.Many2one(related='product_id.uom_id')
