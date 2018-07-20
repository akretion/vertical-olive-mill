# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
import odoo.addons.decimal_precision as dp


class ResPartner(models.Model):
    _inherit = 'res.partner'

    olive_farmer = fields.Boolean('Olive Farmer')
    olive_tree_total = fields.Integer(
        compute='_compute_olive_total', string='Total Trees', readonly=True)
    olive_area_total = fields.Float(
        compute='_compute_olive_total', string='Total Area', readonly=True,
        digits=dp.get_precision('Area'))
    # caisses pretes + palox pretes

    @api.onchange('olive_farmer')
    def olive_farmer_change(self):
        if self.olive_farmer:
            self.customer = True
            self.supplier = True

    def _compute_olive_total(self):
        for partner in self:
            tree = 0
            area = 0.0
            if partner.olive_farmer and not partner.parent_id:
                try:
                    parcels = self.env['olive.parcel'].search([('partner_id', '=', partner.id)])
                    for parcel in parcels:
                        tree += parcel.tree_qty
                        area += parcel.area
                except Exception:
                    pass
            partner.tree = tree
            partner.area = area
