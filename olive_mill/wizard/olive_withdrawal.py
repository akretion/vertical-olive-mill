# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, _
from odoo.exceptions import UserError


class OliveWithdrawal(models.TransientModel):
    _name = 'olive.withdrawal'
    _description = 'Wizard to withdraw olive oil'

    partner_id = fields.Many2one(
        'res.partner', string='Olive Farmer', required=True,
        domain=[('olive_farmer', '=', True)])
    olive_cultivation_form_ko = fields.Boolean(
        related='partner_id.commercial_partner_id.olive_cultivation_form_ko',
        readonly=True)
    olive_parcel_ko = fields.Boolean(
        related='partner_id.commercial_partner_id.olive_parcel_ko', readonly=True)
    olive_organic_certif_ko = fields.Boolean(
        related='partner_id.commercial_partner_id.olive_organic_certif_ko',
        readonly=True)
    olive_invoicing_ko = fields.Boolean(
        related='partner_id.commercial_partner_id.olive_invoicing_ko',
        readonly=True)
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Olive Mill', required=True,
        default=lambda self: self.env.user._default_olive_mill_wh())

    def _prepare_picking(self):
        src_loc = self.warehouse_id.olive_withdrawal_loc_id
        commercial_partner = self.partner_id.commercial_partner_id
        quants_group_product = self.env['stock.quant'].read_group([
            ('location_id', '=', src_loc.id),
            ('reservation_id', '=', False),
            ('owner_id', '=', commercial_partner.id),
            ], ['product_id', 'qty'], ['product_id'])
        if not quants_group_product:
            raise UserError(_(
                "There are no unreserved quants on the stock location '%s' "
                "owned by '%s'") % (
                    src_loc.display_name,
                    commercial_partner.display_name))
        moves = []
        for quant_gp in quants_group_product:
            product_id = quant_gp['product_id'][0]
            product = self.env['product.product'].browse(product_id)
            mvals = {
                'name': _('Withdrawal of Olive Oil'),
                'product_id': product_id,
                'location_id': src_loc.id,
                'location_dest_id': self.partner_id.property_stock_customer.id,
                'product_uom': product.uom_id.id,
                'product_uom_qty': quant_gp['qty'],
                'origin': _('Olive Withdrawal Wizard'),
                'restrict_partner_id': commercial_partner.id,
                }
            moves.append((0, 0, mvals))
        vals = {
            'partner_id': self.partner_id.id,
            'picking_type_id': self.warehouse_id.out_type_id.id,
            'move_lines': moves,
            'origin': _('Olive Withdrawal Wizard'),
            'location_id': src_loc.id,
            'location_dest_id': commercial_partner.property_stock_customer.id,
            }
        return vals

    def validate(self):
        self.ensure_one()
        if not self.warehouse_id.olive_withdrawal_loc_id:
            raise UserError(_(
                "Missing Olive Oil Withdrawal Location on "
                "warehouse '%s'") % self.warehouse_id.display_name)
        vals = self._prepare_picking()
        pick = self.env['stock.picking'].create(vals)
        pick.action_confirm()
        pick.action_assign()
        action = self.env['ir.actions.act_window'].for_xml_id(
            'stock', 'action_picking_tree_all')
        action.update({
            'res_id': pick.id,
            'views': False,
            'view_mode': 'form,tree,kanban,calendar',
            })
        return action
