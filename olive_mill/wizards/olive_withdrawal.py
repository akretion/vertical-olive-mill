# Copyright 2018-2023 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, _
from odoo.exceptions import UserError


class OliveWithdrawal(models.TransientModel):
    _name = 'olive.withdrawal'
    _description = 'Wizard to withdraw olive oil'
    _check_company_auto = True

    company_id = fields.Many2one(
        'res.company', ondelete='cascade', required=True,
        default=lambda self: self.env.company)
    partner_id = fields.Many2one(
        'res.partner', string='Olive Farmer', required=True,
        domain=[('olive_farmer', '=', True)])
    olive_cultivation_form_ko = fields.Boolean(
        related='partner_id.commercial_partner_id.olive_cultivation_form_ko',
        readonly=True)
    olive_parcel_ko = fields.Boolean(
        related='partner_id.commercial_partner_id.olive_parcel_ko', readonly=True)
    olive_organic_certif_ko = fields.Boolean(
        related='partner_id.commercial_partner_id.olive_organic_certif_ko')
    olive_invoicing_ko = fields.Boolean(
        related='partner_id.commercial_partner_id.olive_invoicing_ko')
    olive_withdrawal_ko = fields.Boolean(
        related='partner_id.commercial_partner_id.olive_withdrawal_ko')
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Olive Mill', required=True, check_company=True,
        domain="[('olive_mill', '=', True), ('company_id', '=', company_id)]",
        default=lambda self: self.env.user._default_olive_mill_wh())

    def _prepare_move_vals(self, picking):
        src_loc = self.warehouse_id.olive_withdrawal_loc_id
        commercial_partner = self.partner_id.commercial_partner_id
        location_dest_id = commercial_partner.property_stock_customer.id
        quants = self.env['stock.quant'].search([
            ('location_id', '=', src_loc.id),
            ('owner_id', '=', commercial_partner.id),
            ('quantity', '>', 0),
            ], order="product_id")
        if not quants:
            raise UserError(_(
                "There are no quants on the stock location '%s' "
                "owned by '%s'.") % (
                    src_loc.display_name,
                    commercial_partner.display_name))
        mlines = self.env['stock.move.line'].search([
            ('state', 'not in', ('done', 'cancel')),
            ('company_id', '=', self.company_id.id),
            ('owner_id', '=', commercial_partner.id),
            ('location_id', '=', src_loc.id),
            ('location_dest_id', '=', location_dest_id),
            ])
        if mlines:
            other_pickings = self.env['stock.picking']
            for mline in mlines:
                if mline.picking_id:
                    other_pickings |= mline.picking_id
            raise UserError(_("There are ongoing withdrawal pickings for olive farmer '%s': %s. It probably means that you have already launched this wizard.") % (commercial_partner.display_name, ', '.join([p.name for p in other_pickings])))
        mvals_list = []
        for quant in quants:
            product = quant.product_id
            mvals = {
                'picking_id': picking.id,
                'company_id': self.company_id.id,
                'name': _('Withdrawal of Olive Oil'),
                'product_id': product.id,
                'product_uom': product.uom_id.id,
                'location_id': src_loc.id,
                'location_dest_id': location_dest_id,
                'product_uom_qty': quant.quantity,
                'origin': picking.origin,
                'state': 'assigned',
                'move_line_ids': [(0, 0, {
                    'picking_id': picking.id,
                    'product_id': product.id,
                    'product_uom_id': product.uom_id.id,
                    'product_uom_qty': quant.quantity,
                    'qty_done': quant.quantity,
                    'location_id': src_loc.id,
                    'location_dest_id': location_dest_id,
                    'lot_id': quant.lot_id.id,
                    'owner_id': commercial_partner.id,
                    })],
                }
            mvals_list.append(mvals)
            quant.sudo().write({'reserved_quantity': quant.quantity})
        return mvals_list

    def _prepare_picking(self):
        vals = {
            'company_id': self.company_id.id,
            'partner_id': self.partner_id.id,
            'picking_type_id': self.warehouse_id.out_type_id.id,
            'origin': _('Olive Withdrawal Wizard'),
            'location_id': self.warehouse_id.olive_withdrawal_loc_id.id,
            'location_dest_id': self.partner_id.commercial_partner_id.property_stock_customer.id,
            'state': 'assigned',
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
        move_vals_list = self._prepare_move_vals(pick)
        self.env['stock.move'].create(move_vals_list)
        action = self.env['ir.actions.actions']._for_xml_id(
            'stock.action_picking_tree_all')
        action.update({
            'res_id': pick.id,
            'views': False,
            'view_mode': 'form,tree,kanban,calendar',
            })
        return action
