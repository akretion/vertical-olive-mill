# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class OliveLendedCase(models.Model):
    _name = 'olive.lended.case'
    _description = 'Olive Lended Case'
    _order = 'date desc'

    partner_id = fields.Many2one(
        'res.partner', string='Olive Farmer',
        domain=[('parent_id', '=', False), ('olive_farmer', '=', True)],
        ondelete='restrict')
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env['res.company']._company_default_get(
            'olive.season'))
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    qty = fields.Integer(
        string='Quantity', required=True,
        help="The quantity is positive when the case is lended, negative when the case is returned.")
    notes = fields.Char(string='Notes')
    # M2O to incoming or origin field

    _sql_constrains = [(
        'qty_not_null',
        'CHECK(qty <> 0)',
        'The quantity must be not null.')]
