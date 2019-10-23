# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round
import odoo.addons.decimal_precision as dp


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
    olive_season_year = fields.Char(
        related='olive_season_id.year', store=True)
    oil_product_id = fields.Many2one(
        'product.product', string='Oil Product',
        domain=[('olive_type', '=', 'oil')])
    olive_shrinkage_oil_product_ids = fields.Many2many(
        'product.product', 'stock_location_shrinkage_oil_product_rel',
        'location_id', 'product_id', domain=[('olive_type', '=', 'oil')],
        string='Allowed Oil Products')
    olive_oil_qty = fields.Float(
        compute='_compute_olive_oil_qty', readonly=True,
        string='Olive Oil Qty (L)',
        digits=dp.get_precision('Product Unit of Measure'))

    def _compute_olive_oil_qty(self):
        prec = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        rg_res = self.env['stock.quant'].read_group(
            [('location_id', 'in', self.ids)],
            ['qty', 'location_id'],
            ['location_id'])
        for rg_re in rg_res:
            loc = self.browse(rg_re['location_id'][0])
            qty = loc.olive_tank_type and rg_re['qty'] and float_round(rg_re['qty'], precision_digits=prec) or 0
            loc.olive_oil_qty = qty

    @api.onchange('olive_tank_type')
    def olive_tank_type_change(self):
        if self.olive_tank_type:
            if not self.olive_season_id:
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

    def olive_oil_tank_check(self, raise_if_not_merged=True, raise_if_empty=True):
        '''Returns quantity
        Always raises when there are reservations
        '''
        self.ensure_one()
        sqo = self.env['stock.quant']
        ppo = self.env['product.product']
        prec = self.env['decimal.precision'].precision_get('Product Unit of Measure')
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
        if self.oil_product_id.olive_type != 'oil':
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
            ['qty'], [])
        qty = quant_qty_rg and quant_qty_rg[0]['qty'] or 0
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
        reserved_quants_count = sqo.search([
            ('location_id', '=', self.id), ('reservation_id', '!=', False)],
            count=True)
        if reserved_quants_count:
            raise UserError(_(
                "There are %d reserved quants in tank '%s'.")
                % (reserved_quants_count, self.name))

        if raise_if_not_merged:
            quant_lot_rg = sqo.read_group(
                [('location_id', '=', self.id)],
                ['qty', 'lot_id'], ['lot_id'])
            if len(quant_lot_rg) > 1:
                raise UserError(_(
                    "The tank '%s' (type '%s') is not merged: it "
                    "contains several different lots.") % (
                        self.name, tank_type_label))
            # for risouletto, there are additionnal checks for raise_if_not_merged
            # see below

        quant_product_rg = sqo.read_group(
            [('location_id', '=', self.id)],
            ['qty', 'product_id'], ['product_id'])
        if tank_type == 'risouletto':
            for quant_product in quant_product_rg:
                product = ppo.browse(quant_product['product_id'][0])
                if raise_if_not_merged and product != self.oil_product_id:
                    raise UserError(_(
                        "The tank '%s' (type '%s') contains '%s', "
                        "so it not merged.") % (
                            self.name, tank_type_label, product.display_name))
                if product.olive_type != 'oil':
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
            partial_transfer_qty=False, origin=False, auto_validate=False):
        self.ensure_one()
        assert transfer_type in ('partial', 'full'), 'wrong transfer_type arg'
        if dest_loc == self:
            raise UserError(_(
                "You are trying to transfer oil from '%s' to the same location!")
                % self.display_name)
        sqo = self.env['stock.quant']
        smo = self.env['stock.move']
        pr_oil = self.env['decimal.precision'].precision_get('Olive Oil Volume')
        src_loc = self
        raise_if_not_merged = False
        if transfer_type == 'partial':
            raise_if_not_merged = True
        src_qty = src_loc.olive_oil_tank_check(
            raise_if_not_merged=raise_if_not_merged)
        # compat src/dest
        if dest_loc.olive_tank_type:
            dest_loc.olive_oil_tank_check(
                raise_if_not_merged=False, raise_if_empty=False)
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
