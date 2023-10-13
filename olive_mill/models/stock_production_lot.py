# Copyright 2018-2023 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.misc import format_date


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    olive_production_id = fields.Many2one(
        'olive.oil.production', string='Olive Oil Production', ondelete='restrict',
        readonly=True)
    product_detailed_type = fields.Selection(related='product_id.detailed_type', store=True)

    @api.depends('name', 'expiry_date', 'olive_production_id')
    def name_get(self):
        res = []
        today = fields.Date.context_today(self)
        for lot in self:
            dname = lot.name
            if lot.expiry_date:
                expiry_date_print = format_date(self.env, lot.expiry_date)
                if lot.expiry_date < today:
                    dname = _("[%s Expired] %s") % (expiry_date_print, dname)
                else:
                    dname = "[%s] %s" % (expiry_date_print, dname)
            if lot.olive_production_id:
                dname = '%s (%s)' % (dname, lot.olive_production_id.farmers)
            res.append((lot.id, dname))
        return res

    def browse_recursive_tree(self, oil_prod_ids):
        self.ensure_one()
        assert self.product_id.detailed_type in ('olive_oil', 'olive_bottle_full')
        if self.olive_production_id:
            oil_prod_ids.add(self.olive_production_id.id)
        else:
            move_lines = self.env['stock.move.line'].search([
                ('state', '=', 'done'),
                ('lot_id', '=', self.id),
                ('company_id', '=', self.company_id.id),
                ('move_id.production_id', '!=', False),
                ])
            for move_line in move_lines:
                for consume_move_line in move_line.consume_line_ids:
                    if (
                            consume_move_line.product_id.detailed_type in ('olive_oil', 'olive_bottle_full') and
                            consume_move_line.lot_id and
                            consume_move_line.lot_id.id != self.id):
                        consume_move_line.lot_id.browse_recursive_tree(oil_prod_ids)

    def report_get_arrival_lines(self):
        self.ensure_one()
        if self.product_id.detailed_type not in ('olive_bottle_full', 'olive_oil'):
            raise UserError(_(
                "The product '%s' is not a 'Full Oil Bottle' nor "
                "'Olive Oil'. This report is only for this type of products.")
                % self.product_id.display_name)
        if not self.quant_ids:
            raise UserError(_(
                "The production lot '%s' is not linked to a quant.")
                % self.display_name)
        oil_prod_ids = set()
        self.browse_recursive_tree(oil_prod_ids)
        oil_productions = self.env['olive.oil.production'].browse(list(oil_prod_ids))
        arrival_lines = oil_productions.line_ids
        tmp_list = sorted(arrival_lines, key=lambda to_sort: to_sort.arrival_date)
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
