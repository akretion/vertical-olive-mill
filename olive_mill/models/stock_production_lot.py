# -*- coding: utf-8 -*-
# Copyright 2018-2019 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError


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

    @api.model
    def browse_recursive_tree(self, root_quant, lines):
        if (
                root_quant.product_id and
                root_quant.product_id.olive_type in ('oil', 'bottle_full')):
            lot = root_quant.lot_id
            if not lot:
                    raise UserError(_(
                        "The quant ID %d of the olive oil product '%s' "
                        "is not linked to a lot !") % (
                            root_quant.id, root_quant.product_id.display_name))
            if lot.olive_production_id:
                for line in lot.olive_production_id.line_ids:
                    lines[line] = True
            elif root_quant.consumed_quant_ids:
                for cquant in root_quant.consumed_quant_ids:
                    self.browse_recursive_tree(cquant, lines)

    def report_get_arrival_lines(self):
        self.ensure_one()
        if not self.product_id.olive_type:
            raise UserError(_(
                "The product '%s' has no olive type.")
                % self.product_id.display_name)
        if self.product_id.olive_type not in ('bottle_full', 'oil'):
            raise UserError(_(
                "The product '%s' has an olive type '%s'. This report is only "
                "for products with olive type 'Full Oil Bottle' or "
                "Olive Oil'.") % (
                    self.product_id.display_name, self.product_id.olive_type))
        if not self.quant_ids:
            raise UserError(_(
                "The production lot '%s' is not linked to a quant.")
                % self.display_name)
        quant = self.quant_ids[0]
        lines = {}  # dict to avoid double entries in arrival lines
        self.browse_recursive_tree(quant, lines)
        tmp_list = sorted(lines.keys(), key=lambda to_sort: to_sort.arrival_date)
        res = {}
        for line in tmp_list:
            if line.commercial_partner_id in res:
                res[line.commercial_partner_id]['lines'] += line
                res[line.commercial_partner_id]['subtotal'] += line.olive_qty
            else:
                res[line.commercial_partner_id] = {
                    'lines': line,
                    'subtotal': line.olive_qty,
                    }
        # from pprint import pprint
        # pprint(res)
        return res
