# Copyright 2018-2023 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.tools.misc import format_date


class OliveLendedCase(models.Model):
    _name = 'olive.lended.case'
    _description = 'Olive Lended Cases'
    _order = 'date desc'
    _check_company_auto = True

    partner_id = fields.Many2one(
        'res.partner', string='Olive Farmer',
        domain=[('parent_id', '=', False), ('olive_farmer', '=', True)],
        ondelete='restrict', index=True)
    olive_culture_type = fields.Selection(related='partner_id.olive_culture_type')
    warehouse_id = fields.Many2one(
        'stock.warehouse', required=True, check_company=True,
        domain="[('olive_mill', '=', True), ('company_id', '=', company_id)]",
        default=lambda self: self.env.user._default_olive_mill_wh())
    season_id = fields.Many2one(
        'olive.season', required=True, index=True, check_company=True,
        default=lambda self: self.env.company.current_season_id.id,
        ondelete='restrict', domain="[('company_id', '=', company_id)]")
    current_season = fields.Boolean(
        compute='_compute_current_season', search='_search_current_season')
    company_id = fields.Many2one(
        'res.company', index=True, required=True,
        ondelete='cascade', default=lambda self: self.env.company)
    date = fields.Date(required=True, default=fields.Date.context_today)
    regular_qty = fields.Integer(
        string='Case Quantity',
        help="The quantity is positive when the case is lended. "
        "It is negative when the case is returned.")
    organic_qty = fields.Integer(
        string='Organic Case Quantity',
        help="The quantity is positive when the case is lended. "
        "It is negative when the case is returned.")
    notes = fields.Char(string='Notes')

    def _compute_current_season(self):
        for lcase in self:
            if lcase.company_id.current_season_id == lcase.season_id:
                lcase.current_season = True
            else:
                lcase.current_season = False

    def _search_current_season(self, operator, value):
        return self.env['res.company']._search_current_season(operator, value)

    @api.depends('date', 'partner_id', 'regular_qty', 'organic_qty')
    def name_get(self):
        res = []
        for rec in self:
            name = '%s, %s, %d | %d' % (
                format_date(self.env, rec.date),
                rec.partner_id.name,
                rec.regular_qty,
                rec.organic_qty)
            res.append((rec.id, name))
        return res
