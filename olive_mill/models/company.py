# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import models, fields, api
import odoo.addons.decimal_precision as dp


class ResCompany(models.Model):
    _inherit = 'res.company'

    olive_max_qty_per_palox = fields.Integer(
        string='Maximum Quantity of Olives per Palox', default=500)
    olive_harvest_arrival_max_delta_days = fields.Integer(
        string='Maximum Delay Between Harvest Start Date and Arrival Date',
        default=3,
        help="If the delay between the harvest start date and the arrival "
        "date is superior to the number of days indicated here, Odoo will "
        "display a warning upon arrival validation when the oil destination "
        "is sale or mix.")
    current_season_id = fields.Many2one(
        'olive.season', compute='_compute_current_season_id', readonly=True,
        string='Current Season')
    # Pre-season polls
    olive_preseason_poll_ratio_no_history = fields.Float(
        string='Ratio for Olive Farmers without History',
        default=15, digits=dp.get_precision('Olive Oil Ratio'))
    # START APPOINTMENTS
    olive_appointment_qty_per_palox = fields.Integer(
        string='Quantity of Olives per Palox', default=380)
    olive_appointment_arrival_no_leaf_removal_minutes = fields.Integer(
        string='Arrival Appointment Default Duration without Leaf Removal', default=3,
        help="Number of minutes per 100 kg of olives")
    olive_appointment_arrival_leaf_removal_minutes = fields.Integer(
        string='Arrival Appointment Default Duration with Leaf Removal', default=8,
        help="Number of minutes per 100 kg of olives")
    olive_appointment_arrival_min_minutes = fields.Integer(
        string='Arrival Appointment Minimum Duration', default=5,
        help="Arrival appointment minimum duration in minutes")
    olive_appointment_lend_minutes = fields.Integer(
        string='Lend Palox/Cases Appointment Default Duration', default=5)
    olive_appointment_withdrawal_minutes = fields.Integer(
        string='Withdrawal Appointment Default Duration', default=5)
    # END APPOINTMENTS
    olive_shrinkage_ratio = fields.Float(
        string='Shrinkage Ratio', default=0.4,
        digits=dp.get_precision('Olive Oil Ratio'))
    olive_filter_ratio = fields.Float(
        string='Filter Loss Ratio', default=1.0,
        digits=dp.get_precision('Olive Oil Ratio'))
    olive_min_ratio = fields.Float(
        string='Minimum Ratio', default=5,
        digits=dp.get_precision('Olive Oil Ratio'),
        help="A ratio under that value would be considered as not realistic "
        "and would trigger a blocking error message.")
    olive_max_ratio = fields.Float(
        string='Maximum Ratio', default=35,
        digits=dp.get_precision('Olive Oil Ratio'),
        help="A ratio above that value would be considered as not realistic "
        "and would trigger a blocking error message.")
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
        domain=[('olive_type', '=', 'tax')])
    olive_oil_early_bird_discount_product_id = fields.Many2one(
        'product.product', string='Early Bird Discount Product',
        domain=[('olive_type', '=', 'service')])
    olive_oil_production_start_hour = fields.Integer(
        string='Default Oil Production Start Hour', default=8)
    olive_oil_production_start_minute = fields.Integer(
        string='Default Oil Production Start Minute', default=0)
    olive_oil_production_duration_minutes = fields.Integer(
        string='Default Oil Production Duration', default=30)
    olive_oil_analysis_default_user_id = fields.Many2one(
        'res.users', string='Default User for Olive Oil Analysis')
    # olive_oil_tax_price_unit = fields.Float(
    #    string='AFIDOL Tax Unit Price',
    #    digits=dp.get_precision('Olive Oil Tax Price Unit'), default=0.129,
    #    help='Tax unit price per liter of olive oil')

    _sql_constraints = [(
        'olive_max_qty_per_palox_positive',
        'CHECK(olive_max_qty_per_palox >= 0)',
        'Maximum Quantity of Olives per Palox must be positive.'), (
        'olive_harvest_arrival_max_delta_days_positive',
        'CHECK(olive_harvest_arrival_max_delta_days >= 0)',
        'Maximum Delay Between Harvest Start Date and Arrival Date '
        'must be positive.'), (
        'olive_preseason_poll_ratio_no_history_positive',
        'CHECK(olive_preseason_poll_ratio_no_history >= 0)',
        'Ratio for Olive Farmers without History must be positive.'), (
        'olive_oil_density_positive',
        'CHECK(olive_oil_density > 0)',
        'Olive oil density must be strictly positive.'), (
        'olive_shrinkage_ratio_positive',
        'CHECK(olive_shrinkage_ratio >= 0)',
        'Shrinkage Ratio must be positive.'), (
        'olive_filter_ratio_positive',
        'CHECK(olive_filter_ratio >= 0)',
        'Filter Ratio must be positive.'), (
        'olive_min_ratio_positive',
        'CHECK(olive_min_ratio >= 0)',
        'Olive Min Ratio must be positive.'), (
        'olive_max_ratio_positive',
        'CHECK(olive_max_ratio >= 0)',
        'Olive Max Ratio must be positive.'), (
        'olive_appointment_qty_per_palox_positive',
        'CHECK(olive_appointment_qty_per_palox >= 0)',
        'The Quantity of Olives per Palox must be positive.'), (
        'olive_appointment_arrival_no_leaf_removal_minutes_positive',
        'CHECK(olive_appointment_arrival_no_leaf_removal_minutes >= 0)',
        'Arrival Appointment Default Duration without Leaf Removal must be positive.'), (
        'olive_appointment_arrival_leaf_removal_minutes_positive',
        'CHECK(olive_appointment_arrival_leaf_removal_minutes >= 0)',
        'Arrival Appointment Default Duration with Leaf Removal must be positive.'), (
        'olive_appointment_arrival_min_minutes_positive',
        'CHECK(olive_appointment_arrival_min_minutes >= 0)',
        'Arrival Appointment Minimum Duration must be positive.'), (
        'olive_appointment_lend_minutes_positive',
        'CHECK(olive_appointment_lend_minutes >= 0)',
        'Lend Palox/Cases Appointment Default Duration must be positive.'), (
        'olive_appointment_withdrawal_minutes_positive',
        'CHECK(olive_appointment_withdrawal_minutes >= 0)',
        'Withdrawal Appointment Default Duration must be positive.'), (
        'olive_oil_production_start_hour_min',
        'CHECK(olive_oil_production_start_hour >= 0)',
        'Oil Production Start Hour must be between 0 and 23.'), (
        'olive_oil_production_start_hour_max',
        'CHECK(olive_oil_production_start_hour <= 23)',
        'Oil Production Start Hour must be between 0 and 23.'), (
        'olive_oil_production_start_minute_min',
        'CHECK(olive_oil_production_start_minute >= 0)',
        'Oil Production Start Minute must be between 0 and 59.'), (
        'olive_oil_production_start_minute_max',
        'CHECK(olive_oil_production_start_minute <= 59)',
        'Oil Production Start Minute must be between 0 and 59.'), (
        'olive_oil_production_duration_minutes_positive',
        'CHECK(olive_oil_production_duration_minutes >= 0)',
        'Oil Production Duration must be positive.')
        ]

    @api.model
    def olive_oil_liter2kg(self, qty):
        return qty * self.olive_oil_density

    @api.model
    def olive_oil_kg2liter(self, qty):
        return qty * 1.0 / self.olive_oil_density

    def olive_min_max_ratio(self):
        self.ensure_one()
        return (self.olive_min_ratio, self.olive_max_ratio)

    def get_current_season(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        season = self.env['olive.season'].search([
            ('start_date', '<=', today),
            ('end_date', '>=', today),
            ('company_id', '=', self.id),
            ], limit=1)
        if season:
            return season
        season = self.env['olive.season'].search([
            ('year', '=', today[:4]),
            ('company_id', '=', self.id),
            ], limit=1)
        if season:
            return season
        season = self.env['olive.season'].search([
            ('start_date', '<=', today),
            ('company_id', '=', self.id)],
            order='start_date desc', limit=1)
        return season or False

    def _compute_current_season_id(self):
        for company in self:
            company.current_season_id = company.get_current_season()

    def current_season_update(self, fields_view_get_result, view_type):
        self.ensure_one()
        fields_view_get_result['arch'] = fields_view_get_result['arch'].replace(
            "'CURRENT_SEASON_ID'", str(self.current_season_id.id))
        return fields_view_get_result
