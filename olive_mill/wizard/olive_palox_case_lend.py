# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class OlivePaloxCaseLend(models.TransientModel):
    _name = 'olive.palox.case.lend'
    _description = 'Wizard to lend palox and/or cases'

    arrival_id = fields.Many2one(
        'olive.arrival', string='Arrival', readonly=True)
    way = fields.Selection([
        ('lend', 'Lend'),
        ('return', 'Return'),
        ], default='lend', required=True, string='Type', readonly=True)
    partner_id = fields.Many2one(
        'res.partner', string='Olive Farmer', required=True, readonly=True,
        domain=[('olive_farmer', '=', True), ('parent_id', '=', False)])
    lend_palox_ids = fields.Many2many(
        'olive.palox', 'olive_palox_wizard_lend_rel', 'wizard_id', 'palox_id',
        string='Palox')
    return_palox_ids = fields.Many2many(
        'olive.palox', 'olive_palox_wizard_return_rel', 'wizard_id', 'palox_id',
        string='Palox')
    olive_culture_type = fields.Selection(
        related='partner_id.olive_culture_type',
        readonly=True)
    regular_case_qty = fields.Integer(string='Case Qty')
    organic_case_qty = fields.Integer(string='Organic Case Qty')

    @api.model
    def default_get(self, fields_list):
        res = super(OlivePaloxCaseLend, self).default_get(fields_list)
        if res['way'] == 'return' and res['partner_id']:
            palox = self.env['olive.palox'].search([('borrower_partner_id', '=', res['partner_id']), ('borrowed_date', '!=', False)])
            if palox:
                res['return_palox_ids'] = palox.ids
            cases_res = self.env['olive.lended.case'].read_group([
                ('company_id', '=', self.env.user.company_id.id),
                ('partner_id', '=', res['partner_id'])],
                ['regular_qty', 'organic_qty'], [])
            if cases_res:
                res['regular_case_qty'] = cases_res[0]['regular_qty'] or 0
                res['organic_case_qty'] = cases_res[0]['organic_qty'] or 0
        return res

    def validate(self):
        self.ensure_one()
        assert not self.partner_id.parent_id
        if self.way == 'lend' and self.lend_palox_ids:
            self.lend_palox_ids.lend_palox(self.partner_id)
        elif self.way == 'return' and self.return_palox_ids:
            self.return_palox_ids.return_borrowed_palox()
        if self.regular_case_qty < 0 or self.organic_case_qty < 0:
            raise UserError(_(
                "The quantity of cases must be positive"))
        if self.regular_case_qty > 0 or self.organic_case_qty > 0:
            sign = self.way == 'return' and -1 or 1
            self.env['olive.lended.case'].create({
                'partner_id': self.partner_id.id,
                'regular_qty': self.regular_case_qty * sign,
                'organic_qty': self.organic_case_qty * sign,
                })
            if self.arrival_id:
                self.arrival_id.hide_lend_palox_case_button = True
        return
