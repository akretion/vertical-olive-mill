# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import models, fields, api, _
from odoo.exceptions import UserError


class OliveConfigSettings(models.TransientModel):
    _name = 'olive.config.settings'
    _inherit = 'res.config.settings'

    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.user.company_id, required=True)
    olive_qty_per_palox = fields.Integer(
        related='company_id.olive_qty_per_palox')
    olive_max_qty_per_palox = fields.Integer(
        related='company_id.olive_max_qty_per_palox')
    olive_appointment_leaf_removal_minutes = fields.Integer(
        related='company_id.olive_appointment_leaf_removal_minutes')
    olive_appointment_no_leaf_removal_minutes = fields.Integer(
        related='company_id.olive_appointment_no_leaf_removal_minutes')
    olive_appointment_min_minutes = fields.Integer(
        related='company_id.olive_appointment_min_minutes')
    olive_organic_case_stock = fields.Integer(
        related='company_id.olive_organic_case_stock')
    olive_organic_case_total = fields.Integer(
        related='company_id.olive_organic_case_total')
    olive_regular_case_stock = fields.Integer(
        related='company_id.olive_regular_case_stock')
    olive_regular_case_total = fields.Integer(
        related='company_id.olive_regular_case_total')
    olive_shrinkage_ratio = fields.Float(
        related='company_id.olive_shrinkage_ratio')
    olive_filter_ratio = fields.Float(
        related='company_id.olive_filter_ratio')
    olive_oil_density = fields.Float(
        related='company_id.olive_oil_density')
    olive_oil_leaf_removal_product_id = fields.Many2one(
        related='company_id.olive_oil_leaf_removal_product_id')
    olive_oil_production_product_id = fields.Many2one(
        related='company_id.olive_oil_production_product_id')
    olive_oil_tax_product_id = fields.Many2one(
        related='company_id.olive_oil_tax_product_id')
    olive_oil_early_bird_discount_product_id = fields.Many2one(
        related='company_id.olive_oil_early_bird_discount_product_id')
    olive_oil_tax_price_unit = fields.Float(
        related='company_id.olive_oil_tax_price_unit')
