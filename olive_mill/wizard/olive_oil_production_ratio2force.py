# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.tools import float_round
from odoo.exceptions import UserError


class OliveOilProductionRatio2force(models.TransientModel):
    _name = 'olive.oil.production.ratio2force'
    _description = 'Olive Oil Production Ratio2force'

    production_id = fields.Many2one(
        'olive.oil.production', string='Olive Oil Production', required=True)
    farmers = fields.Char(
        related='production_id.farmers', readonly=True)
    palox_id = fields.Many2one(
        related='production_id.palox_id', readonly=True)
    season_id = fields.Many2one(
        related='production_id.season_id', readonly=True)
    oil_product_id = fields.Many2one(
        related='production_id.oil_product_id', readonly=True)
    oil_destination = fields.Selection(
        related='production_id.oil_destination', readonly=True)
    olive_qty = fields.Float(
        related='production_id.olive_qty', readonly=True)
    compensation_type = fields.Selection(
        related='production_id.compensation_type', readonly=True)
    compensation_oil_product_id = fields.Many2one(
        related='production_id.compensation_oil_product_id', readonly=True)
    compensation_last_olive_qty = fields.Float(
        related='production_id.compensation_last_olive_qty', readonly=True)
    compensation_oil_qty = fields.Float(
        related='production_id.compensation_oil_qty', readonly=True)
    oil_qty_kg = fields.Float(
        string='Oil Qty (kg)', digits=dp.get_precision('Olive Weight'),
        required=True)
    oil_qty = fields.Float(
        string='Oil Qty (L)', compute='_compute_all',
        digits=dp.get_precision('Olive Oil Volume'), readonly=True)
    ratio = fields.Float(
        string='Gross Ratio (% L)', compute='_compute_all',
        digits=dp.get_precision('Olive Oil Ratio'), readonly=True)
    sale_location_id = fields.Many2one(
        'stock.location', string='Sale Tank')
    compensation_sale_location_id = fields.Many2one(
        'stock.location', string='Compensation Sale Tank')
    decanter_duration = fields.Integer(string='Decanter Duration')
    decanter_speed = fields.Integer(
        string='Decanter Speed', compute='_compute_decanter_speed',
        readonly=True)

    @api.depends('oil_qty_kg')
    def _compute_all(self):
        pr_oil = self.env['decimal.precision'].precision_get(
            'Olive Oil Volume')
        pr_ratio = self.env['decimal.precision'].precision_get(
            'Olive Oil Ratio')
        for wiz in self:
            density = wiz.production_id.company_id.olive_oil_density
            oil_qty = 0.0
            ratio = 0.0
            if density:
                oil_qty = wiz.oil_qty_kg / density
                oil_qty = float_round(oil_qty, precision_digits=pr_oil)
            # Compute ratio, with compensations
            oil_qty_for_ratio = oil_qty
            if wiz.compensation_type == 'last':
                oil_qty_for_ratio -= wiz.compensation_oil_qty
            elif wiz.compensation_type == 'first':
                oil_qty_for_ratio += wiz.compensation_oil_qty
            if wiz.olive_qty:
                ratio = 100 * oil_qty_for_ratio / wiz.olive_qty
                ratio = float_round(ratio, precision_digits=pr_ratio)
            wiz.ratio = ratio
            wiz.oil_qty = oil_qty

    @api.depends('decanter_duration')
    def _compute_decanter_speed(self):
        for wiz in self:
            decanter_speed = 0
            if wiz.decanter_duration:
                decanter_speed = wiz.olive_qty * 60 / wiz.decanter_duration
            wiz.decanter_speed = decanter_speed

    def validate(self):
        self.ensure_one()
        prod = self.production_id
        min_ratio, max_ratio = prod.company_id.olive_min_max_ratio()
        if self.ratio > max_ratio or self.ratio < min_ratio:
            raise UserError(_(
                "The ratio (%s %%) of production %s is not realistic.")
                % (self.ratio, prod.name))
        vals = {
            'oil_qty_kg': self.oil_qty_kg,
            'oil_qty': self.oil_qty,
            'ratio': self.ratio,
            'decanter_speed': self.decanter_speed,
            'compensation_sale_location_id': self.compensation_sale_location_id.id or False,
            'sale_location_id': self.sale_location_id.id or False,
            }
        prod.write(vals)
        prod.ratio2force()
        return True
