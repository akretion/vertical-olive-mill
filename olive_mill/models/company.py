# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import models, fields, api, _
from odoo.exceptions import UserError
import odoo.addons.decimal_precision as dp


class ResCompany(models.Model):
    _inherit = 'res.company'

    olive_default_warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse')
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
    olive_regular_case_total = fields.Integer(string='Regular Cases Total')
    olive_regular_case_stock = fields.Integer(
        compute='_compute_cases', string='Regular Cases in Stock', readonly=True)
    olive_organic_case_total = fields.Integer(string='Organic Cases Total')
    olive_organic_case_stock = fields.Integer(
        compute='_compute_cases', string='Organic Cases in Stock', readonly=True)
    olive_production_shrinkage_ratio = fields.Float(
        string='Production Shrinkage', default=0.4,
        digits=dp.get_precision('Oil Shrinkage Ratio'),
        help='Production Shrinkage in percentage')
    olive_filter_shrinkage_ratio = fields.Float(
        string='Filter Shrinkage', default=1.0,
        digits=dp.get_precision('Oil Shrinkage Ratio'),
        help='Filter shrinkage in percentage')
    olive_oil_density = fields.Float(
        string='Olive Oil Density', default=0.916,
        digits=dp.get_precision('Oil Density'),
        help='Olive oil density in kg per liter')

    _sql_constraints = [(
        'olive_oil_density_positive',
        'CHECK(olive_oil_density > 0)',
        'Olive oil density must be strictly positive'), (
        'olive_filter_shrinkage_ratio_positive',
        'CHECK(olive_filter_shrinkage_ratio >= 0)',
        'Filter shrinkage ratio must be positive'), (
        'olive_production_shrinkage_ratio_positive',
        'CHECK(olive_production_shrinkage_ratio >= 0)',
        'Production shrinkage ratio must be positive')]

    @api.depends('olive_organic_case_total', 'olive_regular_case_total')
    def _compute_cases(self):
        cases_rg = self.env['olive.lended.case'].read_group(
            [('company_id', 'in', self.ids)],
            ['company_id', 'regular_qty', 'organic_qty'], ['company_id'])
        for company in self:
            organic_qty = 0
            regular_qty = 0
            for case_rg in cases_rg:
                if case_rg.get('company_id') and case_rg['company_id'][0] == company.id:
                    organic_qty = case_rg.get('organic_qty')
                    regular_qty = case_rg.get('regular_qty')
            company.olive_organic_case_stock = company.olive_organic_case_total - organic_qty
            company.olive_regular_case_stock = company.olive_regular_case_total - regular_qty

    @api.model
    def olive_oil_liter2kg(self, qty):
        return qty * self.olive_oil_density

    @api.model
    def olive_oil_kg2liter(self, qty):
        return qty * 1.0 / self.olive_oil_density
