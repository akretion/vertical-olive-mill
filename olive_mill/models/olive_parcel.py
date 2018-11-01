# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
import odoo.addons.decimal_precision as dp


class OliveParcel(models.Model):
    _name = 'olive.parcel'
    _description = 'Olive Tree Parcel'

    ochard_id = fields.Many2one(
        'olive.ochard', string='Ochard', ondelete='cascade', index=True)
    partner_id = fields.Many2one(
        related='ochard_id.partner_id', string='Farmer',
        index=True, store=True, readonly=True)
    land_registry_ref = fields.Char(string='Land Registry Ref')
    area = fields.Float(
        string='Area', digits=dp.get_precision('Olive Parcel Area'),
        help="Area in hectare")
    tree_qty = fields.Integer(string='Number of Trees')
    variant_ids = fields.Many2many('olive.variant', string='Olive Variants')
    variant_label = fields.Char(
        compute='_compute_variant_label', string='Olive Variants',
        store=True, readonly=True)
    density = fields.Char('Density', size=64)
    planted_year = fields.Char(string='Planted Year')
    irrigation = fields.Selection([
        ('dry', 'Dry'),
        ('dripping', 'Dripping'),
        ('micro-sprinkler', 'Micro-Sprinkler'),
        ('spraying', 'Spraying'),
        ], string='Irrigation')
    cultivation_method = fields.Char(string='Cultivation Method', size=128)
    notes = fields.Text(string='Notes')

    _sql_constraints = [(
        'area_positive',
        'CHECK(area >= 0)',
        'The area must be positive or null.'), (
        'tree_qty_positive',
        'CHECK(tree_qty >= 0)',
        "The number of trees must be positive or null."),
        ]

    @api.depends('variant_ids.name')
    def _compute_variant_label(self):
        for parcel in self:
            parcel.variant_label = u', '.join([
                p.name for p in parcel.variant_ids])
