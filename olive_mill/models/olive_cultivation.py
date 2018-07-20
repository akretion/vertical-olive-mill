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
    company_id = fields.Many2one(
        related='season_id.company_id', store=True, readonly=True, string='Company',
        compute_sudo=True)
    partner_id = fields.Many2one(
        related='location_id.partner_id', string='Farmer',
        store=True, readonly=True, compute_sudo=True)
    season_id = fields.Many2one(
        'olive.season', string='Season', required=True,
        default=lambda self: self.env['olive.season'].get_current_season())
    treatment_type = fields.Selection([
        ('treatment', 'Treatment'),
        ('fertilisation', 'Fertilisation'),
        ('weeding', 'Weeding'),  # désherbage
        ], string='Treatment Type')
    treatment_id = fields.Many2one(
        'olive.treatment', string='Treatment Product', ondelete='restrict')
    quantity = fields.Char(string='Quantity')
    notes = fields.Text(string='Notes')
