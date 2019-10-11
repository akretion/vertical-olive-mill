# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class OliveLendedCase(models.Model):
    _name = 'olive.lended.case'
    _description = 'Olive Lended Cases'
    _order = 'date desc'

    partner_id = fields.Many2one(
        'res.partner', string='Olive Farmer',
        domain=[('parent_id', '=', False), ('olive_farmer', '=', True)],
        ondelete='restrict', index=True)
    olive_culture_type = fields.Selection(
        related='partner_id.olive_culture_type', readonly=True)
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse', required=True,
        domain=[('olive_mill', '=', True)],
        default=lambda self: self.env.user._default_olive_mill_wh())
    company_id = fields.Many2one(
        'res.company', string='Company', index=True,
        default=lambda self: self.env['res.company']._company_default_get())
    date = fields.Date(
        string='Date', required=True, default=fields.Date.context_today)
    regular_qty = fields.Integer(
        string='Case Quantity',
        help="The quantity is positive when the case is lended. "
        "It is negative when the case is returned.")
    organic_qty = fields.Integer(
        string='Organic Case Quantity',
        help="The quantity is positive when the case is lended. "
        "It is negative when the case is returned.")
    notes = fields.Char(string='Notes')
