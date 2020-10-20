# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class MrpProductProduce(models.TransientModel):
    _inherit = 'mrp.product.produce'

    default_lot_expiry_date = fields.Date(
        compute='compute_lot_default', readonly=True)
    default_oil_merge_lot = fields.Boolean(
        compute='compute_lot_default', readonly=True)

    @api.multi
    @api.depends('product_id')
    def compute_lot_default(self):
        for wiz in self:
            if wiz.product_id.olive_type == 'bottle':
                wiz.default_lot_expiry_date = self.env.user.company_id.oil_default_expiry_date
            if wiz.product_id.olive_type in ('olive', 'oil'):
                wiz.default_oil_merge_lot = True
