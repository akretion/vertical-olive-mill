# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models
from odoo.tools import float_round


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def olive_delivery_report_arrival(self):
        self.ensure_one()
        pr_ratio = self.env['decimal.precision'].precision_get(
            'Olive Oil Ratio')
        arrivals = self.env['olive.arrival']
        cpartner = self.partner_id.commercial_partner_id
        for pack in self.pack_operation_ids:
            if pack.product_id and pack.product_id.olive_type == 'oil':
                for pack_lot in pack.pack_lot_ids:
                    if pack_lot.lot_id and pack_lot.lot_id.olive_production_id:
                        for line in pack_lot.lot_id.olive_production_id.line_ids:
                            # also check partner to remove first-of-day compensation lots
                            if line.commercial_partner_id == cpartner:
                                arrivals |= line.arrival_id
        res = [arrival for arrival in arrivals]
        res_sorted = []
        if res:
            res_sorted = sorted(res, key=lambda to_sort: to_sort.name)
        rg = self.env['olive.arrival'].read_group(
            [('id', 'in', arrivals.ids)],
            ['olive_qty_pressed', 'oil_qty_net'], [])
        tot_oil_ratio_net = tot_olive_ratio_net = False
        tot_olive_qty = rg[0]['olive_qty_pressed']
        tot_oil_qty_net = rg[0]['oil_qty_net']
        if tot_olive_qty > 0:
            tot_oil_ratio_net = float_round(
                100 * tot_oil_qty_net / tot_olive_qty,
                precision_digits=pr_ratio)
        if tot_oil_qty_net > 0:
            tot_olive_ratio_net = float_round(
                tot_olive_qty / tot_oil_qty_net, precision_digits=2)
        totals = {
            'olive_qty': tot_olive_qty,
            'oil_qty_net': tot_oil_qty_net,
            'oil_ratio_net': tot_oil_ratio_net,
            'olive_ratio_net': tot_olive_ratio_net,
            }
        return (res_sorted, totals)
