# Copyright 2018-2023 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, _
from odoo.exceptions import UserError


class OliveInvoiceCreate(models.TransientModel):
    _name = 'olive.invoice.create'
    _description = 'Wizard to create invoices for olive mill'
    _check_company_auto = True

    company_id = fields.Many2one(
        'res.company', ondelete='cascade', required=True,
        default=lambda self: self.env.company)
    partner_id = fields.Many2one(
        'res.partner', string='Olive Farmer', required=True,
        domain=[('olive_farmer', '=', True)])
    olive_cultivation_form_ko = fields.Boolean(
        related='partner_id.commercial_partner_id.olive_cultivation_form_ko')
    olive_parcel_ko = fields.Boolean(
        related='partner_id.commercial_partner_id.olive_parcel_ko')
    olive_organic_certif_ko = fields.Boolean(
        related='partner_id.commercial_partner_id.olive_organic_certif_ko')
    olive_invoicing_ko = fields.Boolean(
        related='partner_id.commercial_partner_id.olive_invoicing_ko')
    olive_withdrawal_ko = fields.Boolean(
        related='partner_id.commercial_partner_id.olive_withdrawal_ko')
    season_id = fields.Many2one(
        'olive.season', string='Season', required=True, check_company=True,
        domain="[('company_id', '=', company_id)]",
        default=lambda self: self.env.company.current_season_id.id)
    olive_sale_pricelist_id = fields.Many2one(
        related='partner_id.olive_sale_pricelist_id',
        readonly=False)
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Olive Mill', required=True, check_company=True,
        domain="[('olive_mill', '=', True), ('company_id', '=', company_id)]",
        default=lambda self: self.env.user._default_olive_mill_wh())
    invoice_type = fields.Selection([
        ('out', 'Customer Invoice'),
        ('in', 'Supplier Invoice'),
        ('all', 'Supplier and Customer Invoice'),
        ], string='Invoice Type', default='all', required=True)

    def validate(self):
        self.ensure_one()
        oalo = self.env['olive.arrival.line']
        commercial_partner = self.partner_id.commercial_partner_id
        move_ids = []
        if self.invoice_type in ('in', 'all'):
            lines = oalo.search([
                ('commercial_partner_id', '=', commercial_partner.id),
                ('company_id', '=', self.company_id.id),
                ('warehouse_id', '=', self.warehouse_id.id),
                ('season_id', '=', self.season_id.id),
                ('production_state', '=', 'done'),
                ('in_invoice_line_id', '=', False),
                ('oil_destination', 'in', ('sale', 'mix')),
                ('sale_oil_qty', '>', 0),
                ])
            if lines:
                commercial_partner.olive_check_in_invoice_fiscal_position()
                in_invoice = lines.in_invoice_create()
                move_ids.append(in_invoice.id)
        if self.invoice_type in ('all', 'out'):
            lines = oalo.search([
                ('commercial_partner_id', '=', commercial_partner.id),
                ('company_id', '=', self.company_id.id),
                ('warehouse_id', '=', self.warehouse_id.id),
                ('season_id', '=', self.season_id.id),
                ('production_state', '=', 'done'),
                ('out_invoice_id', '=', False),
                ])
            if lines:
                out_invoice = lines.out_invoice_create()
                move_ids.append(out_invoice.id)
        if not move_ids:
            raise UserError(_("No invoice created."))
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Invoices'),
            'res_model': 'account.move',
            'search_view_id': self.env.ref('account.view_account_invoice_filter').id,
            }
        if len(move_ids) == 1:
            action.update({
                'view_mode': 'form,tree,kanban',
                'res_id': move_ids[0],
                })
        else:
            action.update({
                'domain': [('id', 'in', move_ids)],
                'view_mode': 'tree,kanban,form',
                })
        return action
