# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    olive_production_id = fields.Many2one(
        'olive.oil.production', 'Olive Oil Production', ondelete='restrict',
        readonly=True)

    @api.depends('name', 'expiry_date', 'olive_production_id')
    def name_get(self):
        res = []
        for lot in self:
            dname = lot.name
            if lot.expiry_date:
                dname = '[%s] %s' % (lot.expiry_date, dname)
            if lot.olive_production_id:
                dname = u'%s (%s)' % (dname, lot.olive_production_id.farmers)
            res.append((lot.id, dname))
        return res
