# Copyright 2018-2023 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class OliveCultivation(models.Model):
    _name = 'olive.cultivation'
    _description = 'Olive Cultivation Form'
    _check_company_auto = True

    partner_id = fields.Many2one(
        'res.partner', string='Farmer', index=True,
        domain=[('parent_id', '=', False), ('olive_farmer', '=', True)])
    season_id = fields.Many2one(
        'olive.season', string='Season', required=True, index=True, check_company=True,
        default=lambda self: self.env.company.current_season_id.id,
        domain="[('company_id', '=', company_id)]")
    current_season = fields.Boolean(
        compute='_compute_current_season', search='_search_current_season')
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company, ondelete='cascade')
    ochard_ids = fields.Many2many('olive.ochard', string='Ochards')
    date = fields.Date(string="Date")
    treatment_type = fields.Selection([
        ('none', 'No Treatment'),
        ('paper', 'Paper form filled'),
        ('scan', 'See Scan'),
        ('treatment', 'Treatment'),
        ('fertilisation', 'Fertilisation'),
        ('weeding', 'Weeding'),  # désherbage
        ], string='Treatment Type', required=True)
    treatment_id = fields.Many2one(
        'olive.treatment', string='Treatment Product', ondelete='restrict')
    quantity = fields.Char(string='Quantity')
    notes = fields.Text(string='Notes')
    scan = fields.Binary(string='Cultivation Form Scan')
    scan_filename = fields.Char(string='Filename')

    def _compute_current_season(self):
        for cult in self:
            if cult.company_id.current_season_id == cult.season_id:
                cult.current_season = True
            else:
                cult.current_season = False

    def _search_current_season(self, operator, value):
        return self.env['res.company']._search_current_season(operator, value)

    @api.constrains('date', 'season_id')
    def check_cultivation(self):
        today = fields.Date.context_today(self)
        for cult in self:
            if cult.treatment_type == 'scan' and not cult.scan:
                raise ValidationError(_(
                    "You must upload a scan of the cultivation method."))
            if cult.date:
                if cult.date > cult.season_id.end_date:
                    raise ValidationError(_(
                        "On the cultivation form of ochard '%s', "
                        "the date (%s) is after the end of the "
                        "season (%s)") % (
                            cult.ochard_id.display_name, cult.date,
                            cult.season_id.end_date))
                if cult.date > today:
                    raise ValidationError(_(
                        "On the cultivation form of ochard '%s', "
                        "the date (%s) is in the future!")
                        % (cult.ochard_id.display_name, cult.date))

    @api.onchange('treatment_type')
    def treatment_type_change(self):
        if self.treatment_type in ('none', 'scan'):
            self.date = False
            self.treatment_id = False
            self.quantity = False
