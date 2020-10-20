# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import models, fields


class OliveConfigSettings(models.TransientModel):
    _name = 'olive.config.settings'
    _inherit = 'res.config.settings'

    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.user.company_id, required=True)
    current_season_id = fields.Many2one(
        related='company_id.current_season_id', readonly=True)
    olive_preseason_poll_ratio_no_history = fields.Float(
        related='company_id.olive_preseason_poll_ratio_no_history')
    olive_harvest_arrival_max_delta_days = fields.Integer(
        related='company_id.olive_harvest_arrival_max_delta_days')
    olive_max_qty_per_palox = fields.Integer(
        related='company_id.olive_max_qty_per_palox')
    olive_appointment_qty_per_palox = fields.Integer(
        related='company_id.olive_appointment_qty_per_palox')
    olive_appointment_arrival_no_leaf_removal_minutes = fields.Integer(
        related='company_id.olive_appointment_arrival_no_leaf_removal_minutes')
    olive_appointment_arrival_leaf_removal_minutes = fields.Integer(
        related='company_id.olive_appointment_arrival_leaf_removal_minutes')
    olive_appointment_arrival_min_minutes = fields.Integer(
        related='company_id.olive_appointment_arrival_min_minutes')
    olive_appointment_lend_minutes = fields.Integer(
        related='company_id.olive_appointment_lend_minutes')
    olive_appointment_withdrawal_minutes = fields.Integer(
        related='company_id.olive_appointment_withdrawal_minutes')
    olive_shrinkage_ratio = fields.Float(
        related='company_id.olive_shrinkage_ratio')
    olive_filter_ratio = fields.Float(
        related='company_id.olive_filter_ratio')
    olive_min_ratio = fields.Float(
        related='company_id.olive_min_ratio')
    olive_max_ratio = fields.Float(
        related='company_id.olive_max_ratio')
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
    olive_oil_production_start_hour = fields.Integer(
        related='company_id.olive_oil_production_start_hour')
    olive_oil_production_start_minute = fields.Integer(
        related='company_id.olive_oil_production_start_minute')
    olive_oil_analysis_default_user_id = fields.Many2one(
        related='company_id.olive_oil_analysis_default_user_id')
    olive_oil_production_duration_minutes = fields.Integer(
        related='company_id.olive_oil_production_duration_minutes')
