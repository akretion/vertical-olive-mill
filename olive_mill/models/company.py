# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import models, fields, api
import odoo.addons.decimal_precision as dp


class ResCompany(models.Model):
    _inherit = 'res.company'

    olive_qty_per_palox = fields.Integer(
        string='Quantity of Olives per Palox', default=380)
    olive_max_qty_per_palox = fields.Integer(
        string='Maximum Quantity of Olives per Palox', default=500)
    olive_appointment_no_leaf_removal_minutes = fields.Integer(
        string='Appointment Duration without Leaf Removal', default=3,
        help="Number of minutes per 100 kg of olives")
    olive_appointment_leaf_removal_minutes = fields.Integer(
        string='Appointment Duration with Leaf Removal', default=8,
        help="Number of minutes per 100 kg of olives")
    olive_appointment_min_minutes = fields.Integer(
        string='Appointment Minimum Duration', default=5,
        help="Appointment minimum duration in minutes")
    olive_shrinkage_ratio = fields.Float(
        string='Shrinkage Ratio', default=0.4,
        digits=dp.get_precision('Olive Oil Ratio'),
        help='Shrinkage in percentage')
    olive_filter_ratio = fields.Float(
        string='Filter Loss Ratio', default=1.0,
        digits=dp.get_precision('Olive Oil Ratio'),
        help='Filter loss in percentage')
    olive_oil_density = fields.Float(
        string='Olive Oil Density', default=0.916,
        digits=dp.get_precision('Olive Oil Density'),
        help='Olive oil density in kg per liter')
    olive_oil_leaf_removal_product_id = fields.Many2one(
        'product.product', string='Leaf Removal Product',
        domain=[('olive_type', '=', 'service')])
    olive_oil_production_product_id = fields.Many2one(
        'product.product', string='Production Product',
        domain=[('olive_type', '=', 'service')])
    olive_oil_tax_product_id = fields.Many2one(
        'product.product', string='AFIDOL Tax Product',
        domain=[('olive_type', '=', 'service')])
    olive_oil_early_bird_discount_product_id = fields.Many2one(
        'product.product', string='Early Bird Discount Product',
        domain=[('olive_type', '=', 'service')])
    olive_oil_tax_price_unit = fields.Float(
        string='AFIDOL Tax Unit Price',
        digits=dp.get_precision('Olive Oil Tax Price Unit'), default=0.129,
        help='Tax unit price per liter of olive oil')

    _sql_constraints = [(
        'olive_oil_density_positive',
        'CHECK(olive_oil_density > 0)',
        'Olive oil density must be strictly positive'), (
        'olive_filter_shrinkage_ratio_positive',
        'CHECK(olive_filter_shrinkage_ratio >= 0)',
        'Filter shrinkage ratio must be positive'), (
        'olive_production_shrinkage_ratio_positive',
        'CHECK(olive_production_shrinkage_ratio >= 0)',
        'Production shrinkage ratio must be positive'), (
        'olive_oil_tax_price_unit_positive',
        'CHECK(olive_oil_tax_price_unit) >= 0)',
        'Tax unit price must be positive or null')]

    @api.model
    def olive_oil_liter2kg(self, qty):
        return qty * self.olive_oil_density

    @api.model
    def olive_oil_kg2liter(self, qty):
        return qty * 1.0 / self.olive_oil_density
