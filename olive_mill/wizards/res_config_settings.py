# Copyright 2018-2023 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_olive_organic = fields.Boolean(
        string="Organic Olive Mill", implied_group='olive_mill.olive_organic')
    group_olive_compensation = fields.Boolean(
        string="Olive Mill with Compensations", implied_group='olive_mill.olive_compensation')
    current_season_id = fields.Many2one(
        related='company_id.current_season_id')
    olive_preseason_poll_ratio_no_history = fields.Float(
        related='company_id.olive_preseason_poll_ratio_no_history', readonly=False)
    olive_harvest_arrival_max_delta_days = fields.Integer(
        related='company_id.olive_harvest_arrival_max_delta_days', readonly=False)
    olive_max_qty_per_palox = fields.Integer(
        related='company_id.olive_max_qty_per_palox', readonly=False)
    olive_appointment_qty_per_palox = fields.Integer(
        related='company_id.olive_appointment_qty_per_palox', readonly=False)
    olive_appointment_arrival_no_leaf_removal_minutes = fields.Integer(
        related='company_id.olive_appointment_arrival_no_leaf_removal_minutes', readonly=False)
    olive_appointment_arrival_leaf_removal_minutes = fields.Integer(
        related='company_id.olive_appointment_arrival_leaf_removal_minutes', readonly=False)
    olive_appointment_arrival_min_minutes = fields.Integer(
        related='company_id.olive_appointment_arrival_min_minutes', readonly=False)
    olive_appointment_lend_minutes = fields.Integer(
        related='company_id.olive_appointment_lend_minutes', readonly=False)
    olive_appointment_withdrawal_minutes = fields.Integer(
        related='company_id.olive_appointment_withdrawal_minutes', readonly=False)
    olive_shrinkage_ratio = fields.Float(
        related='company_id.olive_shrinkage_ratio', readonly=False)
    olive_filter_ratio = fields.Float(
        related='company_id.olive_filter_ratio', readonly=False)
    olive_min_ratio = fields.Float(
        related='company_id.olive_min_ratio', readonly=False)
    olive_max_ratio = fields.Float(
        related='company_id.olive_max_ratio', readonly=False)
    olive_oil_density = fields.Float(
        related='company_id.olive_oil_density', readonly=False)
    olive_oil_leaf_removal_product_id = fields.Many2one(
        related='company_id.olive_oil_leaf_removal_product_id', readonly=False)
    olive_oil_production_product_id = fields.Many2one(
        related='company_id.olive_oil_production_product_id', readonly=False)
    olive_oil_tax_product_id = fields.Many2one(
        related='company_id.olive_oil_tax_product_id', readonly=False)
    olive_oil_early_bird_discount_product_id = fields.Many2one(
        related='company_id.olive_oil_early_bird_discount_product_id', readonly=False)
    olive_oil_production_start_hour = fields.Integer(
        related='company_id.olive_oil_production_start_hour', readonly=False)
    olive_oil_production_start_minute = fields.Integer(
        related='company_id.olive_oil_production_start_minute', readonly=False)
    olive_oil_analysis_default_user_id = fields.Many2one(
        related='company_id.olive_oil_analysis_default_user_id', readonly=False)
    olive_oil_production_duration_minutes = fields.Integer(
        related='company_id.olive_oil_production_duration_minutes', readonly=False)
