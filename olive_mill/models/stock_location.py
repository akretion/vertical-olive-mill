# Copyright 2018-2023 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare

import logging
logger = logging.getLogger(__name__)


class StockLocation(models.Model):
    _inherit = 'stock.location'

    olive_tank_type = fields.Selection([
        ('regular', 'Regular'),
        ('compensation', 'Compensation'),
        ('shrinkage', 'Shrinkage'),
        ('risouletto', 'Risouletto'),
        ], string='Olive Oil Tank Type')
    olive_season_id = fields.Many2one(
        'olive.season', string='Olive Season', ondelete='restrict')
    olive_season_year = fields.Char(related='olive_season_id.year', store=True)
    oil_product_id = fields.Many2one(
        'product.product', string='Oil Product',
        domain=[('detailed_type', '=', 'olive_oil')])
    olive_shrinkage_oil_product_ids = fields.Many2many(
        'product.product', 'stock_location_shrinkage_oil_product_rel',
        'location_id', 'product_id', domain=[('detailed_type', '=', 'olive_oil')],
        string='Allowed Oil Products')
    olive_oil_qty = fields.Float(
        compute='_compute_olive_oil_qty',
        string='Olive Oil Qty (L)',
        digits='Product Unit of Measure')

    def _compute_olive_oil_qty(self):
        rg_res = self.env['stock.quant'].read_group(
            [('location_id', 'in', self.ids)],
            ['quantity', 'location_id'],
            ['location_id'])
        map_data = dict([(x['location_id'][0], x['quantity']) for x in rg_res])
        for location in self:
            location.olive_oil_qty = map_data.get(location.id, 0)

    @api.onchange('olive_tank_type')
    def olive_tank_type_change(self):
        if self.olive_tank_type:
            if not self.olive_season_id:
                season = self.company_id and self.company_id.current_season_id
                if season:
                    self.olive_season_id = season
        else:
            self.olive_season_id = False

    def name_get(self):
        res = super().name_get()
        new_res = []
        for (location_id, name) in res:
            loc = self.browse(location_id)
            new_name = name
            if loc.olive_tank_type and loc.oil_product_id:
                new_name = '%s (%s, %s)' % (
                    new_name, loc.olive_season_year, loc.oil_product_id.name)
            new_res.append((location_id, new_name))
        return new_res

    def olive_oil_tank_compatibility_check(self, oil_product, season):
        """This method should be called AFTER olive_oil_tank_check()
        so we don't re-do the checks made in olive_oil_tank_check()"""
        self.ensure_one()
        if self.olive_tank_type != 'risouletto':
            if self.oil_product_id != oil_product:
                raise UserError(_(
                    "You are working with oil product '%s', "
                    "but the olive tank '%s' is configured "
                    "with oil product '%s'.") % (
                        oil_product.display_name,
                        self.name,
                        self.oil_product_id.display_name))
            if self.olive_season_id != season:
                raise UserError(_(
                    "You are working with olive season '%s', "
                    "but the olive tank '%s' is configured "
                    "with olive season '%s'.") % (
                        season.name,
                        self.display_name,
                        self.olive_season_id.name))

    def olive_oil_tank_merge(self):
        self.ensure_one()
        # The strategy in this implementation is the following:
        # - for tracability, we need an mrp.production with consume_line_ids
        # - but we don't try to reproduce the regular use of an mrp.production
        # because we don't have a BOM (a constraint blocks BOM with product used both as finished product and raw material)
        # and mrp.production also blocks when the finished product is used in raw move lines
        origin = _('Olive oil tank merge')
        splo = self.env['stock.production.lot']
        sqo = self.env['stock.quant']
        mpo = self.env['mrp.production']
        liter_uom = self.env.ref('uom.product_uom_litre')
        company_id = self.company_id.id
        fin_product = self.oil_product_id
        assert fin_product.tracking == 'lot'
        assert fin_product.detailed_type == 'olive_oil'
        # Check if already merged
        quants = sqo.search([('location_id', '=', self.id)])
        if self.olive_tank_type == 'risouletto':
            if len(quants) == 1 and quants.product_id == self.oil_product_id:
                return
        else:
            if len(quants) == 1:
                return

        # Create finished lot
        merge_lot_name = self.env['ir.sequence'].next_by_code('olive.oil.merge.lot')
        new_lot = splo.create({
            'product_id': fin_product.id,
            'name': merge_lot_name,
            })

        mo = mpo.create({
            'origin': origin,
            'location_src_id': self.id,
            'location_dest_id': self.id,
            'product_id': fin_product.id,
            'product_uom_id': fin_product.uom_id.id,
            'lot_producing_id': new_lot.id,
            })
        logger.info('mrp.production %s created to merge tank %s', mo.display_name, self.display_name)
        # Raw material moves
        total_qty = 0
        raw_moves = self.env['stock.move']
        for quant in quants:
            assert quant.lot_id
            product = quant.product_id
            assert product.uom_id == liter_uom
            total_qty += quant.quantity
            virtualprod_loc_id = product.with_company(company_id).property_stock_production.id
            raw_move_vals = {
                'raw_material_production_id': mo.id,
                'name': product.display_name,
                'origin': origin,
                'company_id': company_id,
                'product_id': product.id,
                'product_uom': product.uom_id.id,
                'product_uom_qty': quant.quantity,
                'location_id': self.id,
                'location_dest_id': virtualprod_loc_id,
                'move_line_ids': [(0, 0, {
                    'product_id': product.id,
                    'product_uom_id': product.uom_id.id,
                    'qty_done': quant.quantity,
                    'location_id': self.id,
                    'location_dest_id': virtualprod_loc_id,
                    'lot_id': quant.lot_id.id,
                    })],
                }
            raw_move = self.env['stock.move'].create(raw_move_vals)
            logger.debug('Generated raw stock.move ID %d', raw_move.id)
            raw_move._action_done()
            raw_moves |= raw_move
        # Finished product move
        virtualprod_loc_id = fin_product.with_company(company_id).property_stock_production.id
        fin_move_vals = {
            'production_id': mo.id,
            'name': fin_product.display_name,
            'origin': origin,
            'company_id': company_id,
            'product_id': fin_product.id,
            'product_uom': fin_product.uom_id.id,
            'product_uom_qty': total_qty,
            'location_id': virtualprod_loc_id,
            'location_dest_id': self.id,
            'move_line_ids': [(0, 0, {
                'product_id': fin_product.id,
                'product_uom_id': fin_product.uom_id.id,
                'qty_done': total_qty,
                'location_id': virtualprod_loc_id,
                'location_dest_id': self.id,
                'lot_id': new_lot.id,
                'consume_line_ids': [(6, 0, raw_moves.move_line_ids.ids)],
            })],
        }
        fin_move = self.env['stock.move'].create(fin_move_vals)
        logger.debug('Generated finished product stock.move ID %d', fin_move.id)
        fin_move._action_done()

        mo.write({
            'state': 'done',
            'product_qty': total_qty,
            'qty_producing': total_qty,
            })
        logger.info('Oil tank %s has been successfully merged', self.display_name)
        return mo

    def olive_oil_tank_check(self, merge_if_not_merged=False, raise_if_empty=True):
        '''Returns quantity
        Always raises when there are reservations
        '''
        self.ensure_one()
        sqo = self.env['stock.quant']
        smlo = self.env['stock.move.line']
        ppo = self.env['product.product']
        prec = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        # delete quants at 0 and merge quants
        sqo._quant_tasks()
        tank_type = self.olive_tank_type
        tank_type_label = dict(self.fields_get('olive_tank_type', 'selection')['olive_tank_type']['selection'])[tank_type]
        # Tank configuration checks
        if not tank_type:
            raise UserError(_(
                "The stock location '%s' is not an olive oil tank.")
                % self.display_name)
        if not self.oil_product_id:
            raise UserError(_(
                "Missing oil product on tank '%s'.") % self.name)
        if self.oil_product_id.detailed_type != 'olive_oil':
            raise UserError(_(
                "Oil product '%s' configured on tank '%s' is not "
                "an olive oil product.") % (
                    self.oil_product_id.display_name, self.name))
        if tank_type != 'risouletto' and not self.olive_season_id:
            raise UserError(_(
                "Olive season is not configured on tank '%s'.") % self.name)

        # raise if empty
        quant_qty_rg = sqo.read_group(
            [('location_id', '=', self.id)],
            ['quantity'], [])
        qty = quant_qty_rg and quant_qty_rg[0]['quantity'] or 0
        fcompare = float_compare(qty, 0, precision_digits=prec)
        if fcompare < 0:
            raise UserError(_(
                "The tank '%s' has a negative quantity (%s).") % (self.name, qty))
        elif fcompare == 0:
            if raise_if_empty:
                raise UserError(_(
                    "The tank '%s' is empty.") % self.name)
            return 0  # WARN : no further checks if empty

        # raise if there are reservations
        mlines_count = smlo.search([
            ('location_id', '=', self.id), ('state', 'not in', ('draft', 'done'))],
            count=True)
        if mlines_count:
            raise UserError(_(
                "There are %d reservations in tank '%s'.")
                % (mlines_count, self.name))

        if merge_if_not_merged:
            self.olive_oil_tank_merge()

        quant_product_rg = sqo.read_group(
            [('location_id', '=', self.id)],
            ['quantity', 'product_id'], ['product_id'])
        if tank_type == 'risouletto':
            for quant_product in quant_product_rg:
                product = ppo.browse(quant_product['product_id'][0])
                if product.detailed_type != 'olive_oil':
                    raise UserError(_(
                        "The tank '%s' (type '%s') contains '%s', "
                        "which is not an olive oil product.") % (
                            self.name, tank_type_label, product.display_name))
        else:  # regular oil => always 1 product, same as configured on tank
            if len(quant_product_rg) > 1:
                raise UserError(_(
                    "There are several different products in tank '%s'. "
                    "This should never happen in an oil tank which is "
                    "not a risouletto tank.") % self.name)
            product = ppo.browse(quant_product_rg[0]['product_id'][0])
            if product != self.oil_product_id:
                raise UserError(_(
                    "The tank '%s' (type '%s') contains '%s' but it is "
                    "configured to contain '%s'. This should never "
                    "happen.") % (
                        self.name, tank_type_label, product.display_name,
                        self.oil_product_id.display_name))
        return qty

    def olive_oil_transfer(
            self, dest_loc, transfer_type, warehouse, dest_partner=False,
            partial_transfer_qty=False, origin=False, olive_oil_production_id=False):
        self.ensure_one()
        assert transfer_type in ('partial', 'full'), 'wrong transfer_type arg'
        if dest_loc == self:
            raise UserError(_(
                "You are trying to transfer oil from '%s' to the same location!")
                % self.display_name)
        spo = self.env['stock.picking']
        smo = self.env['stock.move']
        sqo = self.env['stock.quant']
        pr_oil = self.env['decimal.precision'].precision_get('Olive Oil Volume')
        src_loc = self
        merge_if_not_merged = False
        if transfer_type == 'partial':
            merge_if_not_merged = True
        src_qty = src_loc.olive_oil_tank_check(
            merge_if_not_merged=merge_if_not_merged)
        # compat src/dest
        if dest_loc.olive_tank_type:
            dest_loc.olive_oil_tank_check(raise_if_empty=False)
            dest_loc.olive_oil_tank_compatibility_check(
                src_loc.oil_product_id, src_loc.olive_season_id)

        if not warehouse.int_type_id:
            raise UserError(_(
                "Internal picking type not configured on warehouse %s.")
                % warehouse.display_name)
        virtual_prod_loc_id = src_loc.oil_product_id.property_stock_production.id
        location_dest_id1 = dest_partner and virtual_prod_loc_id or dest_loc.id
        pvals1 = {
            'picking_type_id': warehouse.int_type_id.id,
            'origin': origin,
            'location_id': src_loc.id,
            'location_dest_id': location_dest_id1,
            }
        pick1 = spo.create(pvals1)
        pickings = pick1
        if dest_partner:
            pvals2 = {
                'picking_type_id': warehouse.int_type_id.id,
                'origin': origin,
                'location_id': virtual_prod_loc_id,
                'location_dest_id': dest_loc.id,
                }
            pick2 = spo.create(pvals2)
            pickings |= pick2
        moves = self.env['stock.move']
        # Inspired by stock_quant_package_move_wizard from odoo-usability
        # For the moment, we don't depend on it...
        if transfer_type == 'full':
            quants = sqo.search([('location_id', '=', src_loc.id)])
            for quant in quants:
                if float_compare(quant.quantity, 0, precision_digits=2) <= 0:
                    raise UserError(_(
                        "There is a negative or null quant ID %d on olive tank %s. "
                        "This should never happen.") % (
                            quant.id, src_loc.display_name))
                product_id = quant.product_id.id
                uom_id = quant.product_id.uom_id.id
                mvals1 = {
                    'olive_oil_production_id': olive_oil_production_id,
                    'name': _('Full oil tank transfer'),
                    'origin': origin,
                    'product_id': product_id,
                    'location_id': src_loc.id,
                    'location_dest_id': location_dest_id1,
                    'product_uom': uom_id,
                    'product_uom_qty': quant.quantity,
                    'picking_id': pick1.id,
                    'move_line_ids': [(0, 0, {
                        'picking_id': pick1.id,
                        'product_id': product_id,
                        'product_uom_id': uom_id,
                        'qty_done': quant.quantity,
                        'location_id': src_loc.id,
                        'location_dest_id': location_dest_id1,
                        'lot_id': quant.lot_id.id,
                        })],
                }
                move1 = smo.create(mvals1)
                moves |= move1
                if dest_partner:
                    mvals2 = {
                        'olive_oil_production_id': olive_oil_production_id,
                        'name': _('Full oil tank transfer'),
                        'origin': origin,
                        'product_id': product_id,
                        'location_id': virtual_prod_loc_id,
                        'location_dest_id': dest_loc.id,
                        'product_uom': uom_id,
                        'product_uom_qty': quant.quantity,
                        'picking_id': pick2.id,
                        'move_orig_ids': [(6, 0, [move1.id])],
                        'move_line_ids': [(0, 0, {
                            'picking_id': pick2.id,
                            'product_id': product_id,
                            'product_uom_id': uom_id,
                            'qty_done': quant.quantity,
                            'location_id': virtual_prod_loc_id,
                            'location_dest_id': dest_loc.id,
                            'lot_id': quant.lot_id.id,
                            'owner_id': dest_partner.id,
                            })],
                    }
                    move2 = smo.create(mvals2)
                    moves |= move2

        elif transfer_type == 'partial':
            # we already checked above that the src loc has 1 lot
            if float_compare(partial_transfer_qty, 0, precision_digits=pr_oil) <= 0:
                raise UserError(_(
                    "The quantity to transfer (%s L) must be strictly positive.")
                    % partial_transfer_qty)
            if float_compare(partial_transfer_qty, src_qty, precision_digits=pr_oil) >= 0:
                raise UserError(_(
                    "The quantity to transfer (%s L) from tank '%s' is superior "
                    "to its current oil quantity (%s L).") % (
                        partial_transfer_qty, src_loc.name, src_qty))
            # raise_if_not_merged = True, so we have a single quant/lot
            quant = sqo.search([('location_id', '=', src_loc.id)])
            assert len(quant) == 1
            product_id = src_loc.oil_product_id.id
            uom_id = src_loc.oil_product_id.uom_id.id
            mvals1 = {
                'olive_oil_production_id': olive_oil_production_id,
                'name': _('Partial oil tank transfer'),
                'origin': origin,
                'product_id': product_id,
                'location_id': src_loc.id,
                'location_dest_id': location_dest_id1,
                'product_uom': uom_id,
                'product_uom_qty': partial_transfer_qty,
                'picking_id': pick1.id,
                'move_line_ids': [(0, 0, {
                    'picking_id': pick1.id,
                    'product_id': product_id,
                    'product_uom_id': uom_id,
                    'qty_done': partial_transfer_qty,
                    'location_id': src_loc.id,
                    'location_dest_id': location_dest_id1,
                    'lot_id': quant.lot_id.id,
                    })],
                }
            move1 = smo.create(mvals1)
            moves |= move1
            if dest_partner:
                mvals2 = {
                    'olive_oil_production_id': olive_oil_production_id,
                    'name': _('Partial oil tank transfer'),
                    'origin': origin,
                    'product_id': product_id,
                    'location_id': virtual_prod_loc_id,
                    'location_dest_id': dest_loc.id,
                    'product_uom': uom_id,
                    'product_uom_qty': partial_transfer_qty,
                    'picking_id': pick2.id,
                    'move_orig_ids': [(6, 0, [move1.id])],
                    'move_line_ids': [(0, 0, {
                        'picking_id': pick2.id,
                        'product_id': product_id,
                        'product_uom_id': uom_id,
                        'qty_done': partial_transfer_qty,
                        'location_id': virtual_prod_loc_id,
                        'location_dest_id': dest_loc.id,
                        'lot_id': quant.lot_id.id,
                        'owner_id': dest_partner.id,
                        })],
                    }
                move2 = smo.create(mvals2)
                moves |= move2

            # No need to reserve a particular quant, because we only have 1 lot
            # Hack for dest_partner is at the end of the method
        for move in moves:
            move._action_done()
            assert move.state == 'done'
        return pickings
