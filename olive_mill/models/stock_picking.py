# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.tools import float_round
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    olive_oil_picking_wizard_next_move_id = fields.Many2one(
        'stock.move', compute='_compute_show_start_olive_oil_picking_wizard',
        string='Next Move for Olive Oil Picking Wizard', readonly=True)

    @api.depends('move_lines.product_id.olive_type', 'move_lines.state')
    def _compute_show_start_olive_oil_picking_wizard(self):
        for pick in self:
            move_id = False
            for move in pick.move_lines:
                if (
                        move.state == 'confirmed' and
                        move.product_id.olive_type == 'oil'):
                    move_id = move.id
                    break
            pick.olive_oil_picking_wizard_next_move_id = move_id

    def start_olive_oil_picking_wizard(self):
        self.ensure_one()
        if self.state not in ('confirmed', 'partially_available'):
            raise UserError(_(
                "This wizard can only be started when the picking "
                "is in state 'Confirmed' or 'Partially Available."))
        action = {}
        if self.olive_oil_picking_wizard_next_move_id:
            move = self.olive_oil_picking_wizard_next_move_id
            action = self.env['ir.actions.act_window'].for_xml_id(
                'olive_mill', 'olive_oil_picking_action')
            action['context'] = {
                'default_move_id': move.id,
                'default_oil_product_id': move.product_id.id,
                'default_oil_qty': move.product_uom_qty,
                'default_dest_location_id': move.location_id.id,
                }
        return action

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
