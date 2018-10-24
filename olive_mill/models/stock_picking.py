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
                    # also check partner to remove first-of-day compensation lots
                    if (
                            pack_lot.lot_id and
                            pack_lot.lot_id.arrival_line_id and
                            pack_lot.lot_id.arrival_line_id.commercial_partner_id == cpartner):
                        arrivals |= pack_lot.lot_id.arrival_line_id.arrival_id
        compute = {}
        tot_olive_qty = tot_oil_net = tot_compensation_oil_qty = 0.0
        for arrival in arrivals:
            for l in arrival.line_ids:
                ctype = l.compensation_type
                compensation_oil_qty = False
                if ctype == 'first':
                    compensation_oil_qty = l.compensation_oil_qty
                olive_qty = l.olive_qty
                oil_net = l.oil_qty - l.shrinkage_oil_qty - l.filter_loss_oil_qty
                if l.arrival_id in compute:
                    compute[arrival]['olive_qty'] += olive_qty
                    compute[arrival]['oil_net'] += oil_net
                    compute[arrival]['compensation_oil_qty'] += compensation_oil_qty
                else:
                    compute[arrival] = {
                        'olive_qty': olive_qty,
                        'oil_net': oil_net,
                        'compensation_oil_qty': compensation_oil_qty,
                        }
                tot_olive_qty += olive_qty
                tot_oil_net += oil_net
                tot_compensation_oil_qty += compensation_oil_qty
        res = []
        for arrival, cdict in compute.iteritems():
            oil_with_compensation = cdict['oil_net'] + cdict['compensation_oil_qty']
            oil_ratio_net = olive_ratio_net = False
            if cdict['olive_qty'] > 0:
                oil_ratio_net = float_round(
                    100 * oil_with_compensation / cdict['olive_qty'], precision_digits=pr_ratio)
            if oil_with_compensation > 0:
                olive_ratio_net = float_round(
                    cdict['olive_qty'] / oil_with_compensation, precision_digits=2)
            cdict.update({
                'arrival': arrival,
                'oil_ratio_net': oil_ratio_net,
                'olive_ratio_net': olive_ratio_net,
            })
            res.append(cdict)
        res_sorted = []
        if res:
            res_sorted = sorted(res, key=lambda to_sort: to_sort['arrival'].name)
        tot_oil_ratio_net = tot_olive_ratio_net = False
        tot_oil_with_compensation = tot_oil_net + tot_compensation_oil_qty
        if tot_olive_qty > 0:
            tot_oil_ratio_net = float_round(
                100 * tot_oil_with_compensation / tot_olive_qty,
                precision_digits=pr_ratio)
        if tot_oil_with_compensation > 0:
            tot_olive_ratio_net = float_round(
                tot_olive_qty / tot_oil_with_compensation, precision_digits=2)
        totals = {
            'olive_qty': tot_olive_qty,
            'oil_net': tot_oil_net,
            'compensation_oil_qty': tot_compensation_oil_qty,
            'oil_ratio_net': tot_oil_ratio_net,
            'olive_ratio_net': tot_olive_ratio_net,
            }
        return (res_sorted, totals)
