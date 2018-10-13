# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    arrival_line_id = fields.Many2one(
        'olive.arrival.line', 'Arrival Line', ondelete='restrict',
        readonly=True)
    oil_merge_lot = fields.Boolean(string='Oil Merge Lot', readonly=False)

    @api.depends('name', 'expiry_date', 'oil_merge_lot')
    def name_get(self):
        res = []
        for lot in self:
            dname = lot.name
            if lot.expiry_date:
                dname = '[%s] %s' % (lot.expiry_date, dname)
            if lot.oil_merge_lot:
                dname = '%s %s' % (u'\u2180', dname)
            res.append((lot.id, dname))
        return res

    @api.constrains('oil_merge_lot', 'product_id')
    def check_oil_merge_lot(self):
        for lot in self:
            if (
                    lot.oil_merge_lot and
                    lot.product_id.olive_type not in ('oil', 'olive')):
                raise ValidationError(_(
                    u"Oil Merge Lot can only apply on Olive or Oil products, "
                    u"which is not the case of product '%s'")
                    % lot.product_id.display_name)
