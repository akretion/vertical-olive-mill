# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError, ValidationError


class OliveParcel(models.Model):
    _name = 'olive.parcel'
    _description = 'Olive Tree Parcel'

    ochard_id = fields.Many2one(
        'olive.ochard', string='Ochard', ondelete='cascade')
    partner_id = fields.Many2one(
        related='ochard_id.partner_id', string='Farmer',
        store=True, readonly=True, compute_sudo=True)
    land_registry_ref = fields.Char(string='Land Registry Ref')
    area = fields.Float(
        string='Area', digits=dp.get_precision('Olive Parcel Area'),
        help="Area in hectare")
    tree_qty = fields.Integer(string='Number of trees')
    product_ids = fields.Many2many(  # TODO
        'product.product', string='Olive Types', domain=[('olive_type', '=', 'olive')])
    density = fields.Char('Density', size=64)
    planted_year = fields.Integer('Planted Year')
    irrigation = fields.Selection([
        ('dry', 'Dry'),
        ('dripping', 'Dripping'),
        ('spraying', 'Spraying'),
        ('waterway', 'Waterway'),
        ], string='Irrigation')
    cultivation_method = fields.Char(string='Cultivation Method', size=128)
    notes = fields.Text(string='Notes')

    _sql_constraints = [(
        'area_positive',
        'CHECK(area >= 0)',
        'The area must be positive or 0.'), (
        'tree_qty_positive',
        'CHECK(tree_qty >= 0)',
        "The number of tree must be positive or 0."), (
        'planted_year_positive',
        'CHECK(planted_year >= 0)',
        'The planted year must be positive')]
