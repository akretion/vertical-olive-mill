# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare


class StockLocation(models.Model):
    _inherit = 'stock.location'

    olive_tank_type = fields.Selection([
        ('regular', 'Regular'),
        ('compensation', 'Compensation'),
        ('shrinkage', 'Shrinkage'),
        ], string='Olive Oil Tank Type')
    olive_season_id = fields.Many2one(
        'olive.season', string='Olive Season', ondelete='restrict')
    olive_season_year = fields.Char(
        related='olive_season_id.year', store=True)
    oil_product_id = fields.Many2one(
        'product.product', string='Oil Product',
        domain=[('olive_type', '=', 'oil')])
    olive_shrinkage_oil_product_ids = fields.Many2many(
        'product.product', 'stock_location_shrinkage_oil_product_rel',
        'location_id', 'product_id', domain=[('olive_type', '=', 'oil')],
        string='Allowed Oil Products')

    @api.onchange('olive_tank_type')
    def olive_tank_type_change(self):
        if self.olive_tank_type:
            season = self.env['olive.season'].get_current_season()
            if season:
                self.olive_season_id = season
        else:
            self.olive_season_id = False

    def name_get(self):
        res = super(StockLocation, self).name_get()
        new_res = []
        for entry in res:
            loc = self.browse(entry[0])
            new_name = entry[1]
            if loc.olive_tank_type and loc.oil_product_id:
                new_name = '%s (%s, %s)' % (
                    new_name, loc.olive_season_year, loc.oil_product_id.name)
            new_res.append((entry[0], new_name))
        return new_res

    def olive_oil_qty(self):
        '''This method is a kind of alias to olive_oil_tank_check()'''
        self.ensure_one()
        qty = self.olive_oil_tank_check()
        return qty

    def olive_oil_tank_compatibility_check(self, oil_product, season):
        self.ensure_one()
        if not self.olive_tank_type:
            raise UserError(_(
                "The stock location '%s' is not an olive oil tank.")
                % self.display_name)
        if not self.oil_product_id:
            raise UserError(_(
                "Oil product is not configured on stock location '%s'.")
                % self.display_name)
        if not self.olive_season_id:
            raise UserError(_(
                "Olive season is not configured on stock location '%s'.")
                % self.display_name)
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

    def olive_oil_tank_check(
            self, raise_if_empty=False, raise_if_multi_lot=False,
            raise_if_reservation=False):
        '''Returns quantity'''
        self.ensure_one()
        sqo = self.env['stock.quant']
        ppo = self.env['product.product']
        pr_oil = self.env['decimal.precision'].precision_get('Olive Oil Volume')
        if not self.olive_tank_type:
            raise UserError(_(
                "The stock location '%s' is not an olive oil tank.")
                % self.display_name)
        quant_rg = sqo.read_group(
            [('location_id', '=', self.id)],
            ['qty', 'product_id'], ['product_id'])
        # TODO: handle negative quants ?
        if not quant_rg:
            if raise_if_empty:
                raise UserError(_(
                    "The tank '%s' is empty.") % self.display_name)
            else:
                return 0
        if len(quant_rg) > 1:
            raise UserError(_(
                "There are several different products in tank '%s'. "
                "This should never happen.") % self.name)
        qty = quant_rg[0]['qty']
        if raise_if_empty and float_compare(qty, 0, precision_digits=pr_oil) <= 0:
            raise UserError(_(
                "The tank '%s' is empty.") % self.name)
        if not self.oil_product_id:
            raise UserError(_(
                "Oil product is not configured on tank '%s'.")
                % self.display_name)
        if self.oil_product_id.uom_id != self.env.ref('product.product_uom_litre'):
            raise UserError(_(
                "The unit of measure of product '%s' is '%s' "
                "(it should be liters).") % (
                    self.oil_product_id.display_name,
                    self.oil_product_id.uom_id.name))
        oil_product_id = quant_rg[0]['product_id'][0]
        oil_product = ppo.browse(oil_product_id)
        if oil_product != self.oil_product_id:
            raise UserError(_(
                "The tank '%s' contains '%s' but it is configured "
                "to contain '%s'. This should never happen.") % (
                    self.name, oil_product.display_name,
                    self.oil_product_id.display_name))
        if raise_if_multi_lot:
            quant_lot_rg = sqo.read_group(
                [('location_id', '=', self.id)],
                ['qty', 'lot_id'], ['lot_id'])
            if len(quant_lot_rg) > 1:
                raise UserError(_(
                    "There are several different lots in tank '%s'. "
                    "You may have to merge this tank first.")
                    % self.name)
        if raise_if_reservation:
            reserved_quants_count = sqo.search([
                ('location_id', '=', self.id), ('reservation_id', '!=', False)],
                count=True)
            if reserved_quants_count:
                raise UserError(_(
                    "There are some reserved quants in tank '%s'.")
                    % self.name)
        return qty

    def olive_oil_transfer(
            self, dest_loc, transfer_type, warehouse, dest_partner=False,
            partial_transfer_qty=False, origin=False, auto_validate=False):
        self.ensure_one()
        assert transfer_type in ('partial', 'full'), 'wrong transfer_type arg'
        sqo = self.env['stock.quant']
        smo = self.env['stock.move']
        pr_oil = self.env['decimal.precision'].precision_get('Olive Oil Volume')
        src_loc = self
        raise_if_multi_lot = False
        if transfer_type == 'partial':
            raise_if_multi_lot = True
        src_qty = src_loc.olive_oil_tank_check(
            raise_if_empty=True, raise_if_multi_lot=raise_if_multi_lot)
        # compat src/dest
        if dest_loc.olive_tank_type:
            dest_loc.olive_oil_tank_check()
            dest_loc.olive_oil_tank_compatibility_check(
                src_loc.oil_product_id, src_loc.olive_season_id)

        if not warehouse.int_type_id:
            raise UserError(_(
                "Internal picking type not configured on warehouse %s.")
                % warehouse.display_name)
        vals = {
            'picking_type_id': warehouse.int_type_id.id,
            'origin': origin,
            'location_id': src_loc.id,
            'location_dest_id': dest_loc.id,
            }
        pick = self.env['stock.picking'].create(vals)

        if transfer_type == 'full':
            quants = sqo.search([('location_id', '=', src_loc.id)])
            for quant in quants:
                if float_compare(quant.qty, 0, precision_digits=2) < 0:
                    raise UserError(_(
                        "There is a negative quant ID %d on olive tank %s. "
                        "This should never happen.") % (
                            quant.id, src_loc.display_name))
                if quant.reservation_id:
                    raise UserError(_(
                        "There is a reserved quant ID %d on olive tank %s. "
                        "This must be investigated before trying a tank "
                        "transfer again.") % (quant.id, src_loc.display_name))
                mvals = {
                    'name': _('Full oil tank transfer'),
                    'origin': origin,
                    'product_id': quant.product_id.id,
                    'location_id': src_loc.id,
                    'location_dest_id': dest_loc.id,
                    'product_uom': quant.product_id.uom_id.id,
                    'product_uom_qty': quant.qty,
                    'restrict_lot_id': quant.lot_id.id or False,
                    'restrict_partner_id': quant.owner_id.id or False,
                    'picking_id': pick.id,
                }
                move = smo.create(mvals)
                qvals = {'reservation_id': move.id}
                if dest_partner and quant.owner_id != dest_partner:
                    qvals['owner_id'] = dest_partner.id
                quant.sudo().write(qvals)
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
            product = src_loc.oil_product_id
            mvals = {
                'name': _('Partial oil tank transfer'),
                'origin': origin,
                'product_id': product.id,
                'location_id': src_loc.id,
                'location_dest_id': dest_loc.id,
                'product_uom': product.uom_id.id,
                'product_uom_qty': partial_transfer_qty,
                'picking_id': pick.id,
                }
            move = smo.create(mvals)
            # No need to reserve a particular quant, because we only have 1 lot
            # Hack for dest_partner is at the end of the method
        pick.action_confirm()
        pick.action_assign()
        pick.action_pack_operation_auto_fill()
        if auto_validate:
            pick.do_transfer()
            if transfer_type == 'partial' and dest_partner:
                move.quant_ids.sudo().write({'owner_id': dest_partner.id})
        elif transfer_type == 'partial' and dest_partner:
            raise UserError(
                "We don't support partial transferts without auto_validate and "
                "with dest_partner")
        return pick
