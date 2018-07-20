# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError, ValidationError


class OliveCultivation(models.Model):
    _name = 'olive.cultivation'
    _description = 'Olive Cultivation'

    location_id = fields.Many2one(
        'stock.location', string='Ochard', domain=[('olive_type', '=', 'ochard')], ondelete='restrict')
    partner_id = fields.Many2one(
        related='location_id.partner_id', string='Farmer',
        store=True, readonly=True, compute_sudo=True)
    season_id = fields.Many2one(
        'olive.season', string='Season', required=True,
        default=lambda self: self.env['olive.season'].get_current_season())
    company_id = fields.Many2one(
        related='season_id.company_id', store=True, readonly=True, string='Company',
        compute_sudo=True)
    date = fields.Date(string="Date", required=True)
    treatment_type = fields.Selection([
        ('treatment', 'Treatment'),
        ('fertilisation', 'Fertilisation'),
        ('weeding', 'Weeding'),  # désherbage
        ], string='Treatment Type')
    treatment_id = fields.Many2one(
        'olive.treatment', string='Treatment Product', ondelete='restrict')
    quantity = fields.Char(string='Quantity')
    notes = fields.Text(string='Notes')

    @api.constrains('date', 'season_id')
    def check_cultivation(self):
        today = fields.Date.context_today(self)
        for cult in self:
            if cult.date > cult.season_id.end_date:
                raise ValidationError(_(
                    "On the cultivation method of ochard '%s', the date (%s) is after the "
                    "end of the season (%s)")
                    % (cult.location_id.display_name, cult.date, cult.season_id.end_date))
            if cult.date > today:
                raise ValidationError(_(
                    "On the cultivation method of ochard '%s', the date (%s) is in the future!")
                    % (cult.location_id.display_name, cult.date))
