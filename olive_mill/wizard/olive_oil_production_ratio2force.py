# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.tools import float_round
from odoo.exceptions import UserError

MIN_RATIO = 5
MAX_RATIO = 35


class OliveOilProductionRatio2force(models.TransientModel):
    _name = 'olive.oil.production.ratio2force'
    _description = 'Olive Oil Production Ratio2force'

    olive_oil_production_id = fields.Many2one(
        'olive.oil.production', string='Olive Oil Production', required=True)
    palox_id = fields.Many2one(
        related='olive_oil_production_id.palox_id', readonly=True)
    oil_product_id = fields.Many2one(
        related='olive_oil_production_id.oil_product_id', readonly=True)
    olive_qty = fields.Float(
        related='olive_oil_production_id.olive_qty_compute', readonly=True)
    oil_qty_kg = fields.Float(
        string='Oil Qty', digits=dp.get_precision('Olive Weight'))
    oil_qty = fields.Float(
        string='Oil Qty', compute='_compute_all',
        digits=dp.get_precision('Olive Oil Volume'), readonly=True)
    ratio = fields.Float(
        string='Ratio', compute='_compute_all',
        digits=dp.get_precision('Olive Oil Ratio'), readonly=True)

    @api.depends('oil_qty_kg', 'olive_qty')
    def _compute_all(self):
        oil_prec = self.env['decimal.precision'].precision_get('Olive Oil Volume')
        ratio_prec = self.env['decimal.precision'].precision_get('Olive Oil Ratio')
        for wiz in self:
            oil_qty = 0.0
            ratio = 0.0
            if self.env.user.company_id.olive_oil_density:
                oil_qty = wiz.oil_qty_kg / self.env.user.company_id.olive_oil_density
                oil_qty = float_round(oil_qty, precision_digits=oil_prec)
            if wiz.olive_qty:
                ratio = 100 * oil_qty / wiz.olive_qty
                ratio = float_round(ratio, precision_digits=ratio_prec)
            wiz.ratio = ratio
            wiz.oil_qty = oil_qty

    def validate(self):
        self.ensure_one()
        prod = self.olive_oil_production_id
        if self.ratio > MAX_RATIO or self.ratio < MIN_RATIO:
            raise UserError(_(
                "The ratio (%s %%) of production %s is not realistic.")
                % (self.ratio, prod.name))
        prod.write({'oil_qty_kg': self.oil_qty_kg})
        prod.ratio2force()
        return True
