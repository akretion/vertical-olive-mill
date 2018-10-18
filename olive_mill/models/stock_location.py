# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero, float_round
import odoo.addons.decimal_precision as dp


class StockLocation(models.Model):
    _inherit = 'stock.location'

    olive_tank = fields.Boolean(string='Olive Oil Tank')
    olive_season_id = fields.Many2one(
        'olive.season', string='Season', ondelete='restrict')
    oil_product_id = fields.Many2one(
        'product.product', string='Oil Product',
        domain=[('olive_type', '=', 'oil')])

    def olive_oil_qty(self):
        self.ensure_one()
        # I can't group by on product_uom_id to check that it is L
        # because it's a related non stored field...
        qty = 0.0
        quant_rg = self.check_olive_oil_tank()
        if quant_rg and quant_rg[0].get('qty'):
            qty = quant_rg[0]['qty']
        return qty

    def check_olive_oil_tank(self, raise_if_empty=False):
        self.ensure_one()
        sqo = self.env['stock.quant']
        ppo = self.env['product.product']
        if not self.olive_tank:
            raise UserError(_(
                "The stock location '%s' is not an olive oil tank.")
                % self.display_name)
        quant_rg = sqo.read_group(
            [('location_id', '=', self.id)],
            ['qty', 'product_id'], ['product_id'])
        if not quant_rg:
            if raise_if_empty:
                raise UserError(_(
                    "The tank '%s' is empty.") % self.display_name)
            else:
                return []
        if len(quant_rg) > 1:
            raise UserError(_(
                "There are several different products in tank '%s'. "
                "This should never happen.") % self.display_name)
        if not self.oil_product_id:
            raise UserError(_(
                "Oil product is not configured on tank '%s'.")
                % self.display_name)
        oil_product_id = quant_rg[0]['product_id'][0]
        oil_product = ppo.browse(oil_product_id)
        if oil_product != self.oil_product_id:
            raise UserError(_(
                "The tank '%s' contains '%s' but it is configured "
                "to contain '%s'. This should never happen.") % (
                    self.display_name, oil_product.display_name,
                    self.oil_product_id.display_name))
        return quant_rg

    def olive_oil_transfer(
            self, dest_loc, transfer_type, warehouse, dest_partner=False,
            origin=False, auto_validate=False):
        self.ensure_one()
        sqo = self.env['stock.quant']
        smo = self.env['stock.move']
        src_loc = self
        src_loc.check_olive_oil_tank(raise_if_empty=True)
        # compat src/dest
        if dest_loc.olive_tank:
            dest_loc.check_olive_oil_tank()
            if not dest_loc.oil_product_id:
                dest_loc.oil_product_id = src_loc.oil_product_id.id
            elif dest_loc.oil_product_id != src_loc.oil_product_id:
                raise UserError(_(
                    "The source tank '%s' contains '%s' but the "
                    "destination tank '%s' is configured to "
                    "contain '%s'.") % (
                        src_loc.display_name,
                        src_loc.oil_product_id.display_name,
                        dest_loc.display_name,
                        dest_loc.oil_product_id.display_name))

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
                    'name': _('Full olive oil tank transfer'),
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
        pick.action_confirm()
        pick.action_assign()
        pick.action_pack_operation_auto_fill()
        if auto_validate:
            pick.do_transfer()
        return pick
