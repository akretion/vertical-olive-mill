# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError


class OliveOilProductionForceRatio(models.TransientModel):
    _name = 'olive.oil.production.force.ratio'
    _description = 'Olive Oil Production Force Ratio'

    production_id = fields.Many2one(
        'olive.oil.production', string='Olive Oil Production', required=True)
    palox_id = fields.Many2one(
        related='production_id.palox_id', readonly=True)
    farmers = fields.Char(
        related='production_id.farmers', readonly=True)
    oil_product_id = fields.Many2one(
        related='production_id.oil_product_id', readonly=True)
    global_ratio = fields.Float(
        related='production_id.ratio', readonly=True, string='Global Ratio')
    arrival_line_id = fields.Many2one(
        'olive.arrival.line', required=True, string='Production Line')
    force_ratio = fields.Float(
        string='Force Ratio', digits=dp.get_precision('Olive Oil Ratio'),
        required=True)

    def validate(self):
        self.ensure_one()
        prod = self.production_id
        assert prod.state == 'force'
        line = self.arrival_line_id
        assert line.production_id == prod, 'Line not attached to production'
        min_ratio, max_ratio = prod.company_id.olive_min_max_ratio()
        if self.force_ratio > max_ratio or self.force_ratio < min_ratio:
            raise UserError(_(
                "The ratio (%s %%) is not realistic.") % self.force_ratio)
        prod.set_qty_on_lines(
            force_ratio=(self.arrival_line_id, self.force_ratio))
        return True
