# -*- coding: utf-8 -*-
# Copyright 2020 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OliveOilProductionDoneLast(models.TransientModel):
    _name = 'olive.oil.production.done.last'
    _description = 'Olive Oil Production Done Last'

    last_production_id = fields.Many2one(
        'olive.oil.production', string='Current Last-of-day Production',
        required=True, readonly=True)
    warehouse_id = fields.Many2one(
        related='last_production_id.warehouse_id', readonly=True)
    compensation_location_id = fields.Many2one(
        related='last_production_id.compensation_location_id', readonly=True)
    compensation_oil_product_id = fields.Many2one(
        related='last_production_id.compensation_location_id.oil_product_id',
        readonly=True)
    season_id = fields.Many2one(
        related='last_production_id.season_id', readonly=True)
    next_first_production_id = fields.Many2one(
        'olive.oil.production', string='Next First-of-day Production', readonly=True)
    next_first_compensation_sale_location_id = fields.Many2one(
        'stock.location', string='Compensation Sale Tank', required=True)

    def validate(self):
        self.ensure_one()
        assert self.last_production_id.compensation_type == 'last'
        assert self.next_first_production_id.compensation_type == 'first'
        assert self.last_production_id.compensation_location_id == self.next_first_production_id.compensation_location_id
        self.next_first_production_id.compensation_sale_location_id = self.next_first_compensation_sale_location_id.id
        return True
