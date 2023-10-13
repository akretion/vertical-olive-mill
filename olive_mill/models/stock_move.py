# Copyright 2023 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    olive_oil_production_id = fields.Many2one('olive.oil.production', string='Oil Production', readonly=True, copy=False, check_company=True)


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    olive_oil_production_id = fields.Many2one(related='move_id.olive_oil_production_id', store=True)
