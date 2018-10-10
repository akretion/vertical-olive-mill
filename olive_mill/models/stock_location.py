# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
import odoo.addons.decimal_precision as dp


class StockLocation(models.Model):
    _inherit = 'stock.location'

    olive_tank = fields.Boolean(string='Olive Oil Tank')

    def get_total_liter_kg(self):
        self.ensure_one()
        # I can't group by on product_uom_id to check that it is L
        # because it's a related non stored field...
        quant_rg = self.env['stock.quant'].read_group(
            [('location_id', '=', self.id)], ['qty'], [])
        qty = quant_rg[0].get('qty')
        return qty
