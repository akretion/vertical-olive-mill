# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    oil_merge_lot = fields.Boolean(
        related='lot_id.oil_merge_lot', readonly=True, store=True)

#    def merge_new_lot(self):
#        locs = []
#        for quant in quants:
#            if quant.revervation_id:
#                raise UserError(_(
#                    "Cannot merge quant ID %d of product %s on location %s because "
#                    "it has a reservation.") % ())
#            if quant.location_id.id not in locs:
#                locs.append(quant.location_id.id)
#            if quant.product_id.
