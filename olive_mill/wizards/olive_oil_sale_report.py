# Copyright 2024 Akretion France (https://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import format_date
from odoo.tools import float_is_zero
from dateutil.relativedelta import relativedelta
from collections import defaultdict
import logging
logger = logging.getLogger(__name__)


class OliveOilSaleReport(models.TransientModel):
    _name = 'olive.oil.sale.report'
    _description = 'Olive Oil Sale Report'

    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company)
    start_date = fields.Date(
        required=True,
        default=lambda self: fields.Date.context_today(self) + relativedelta(months=-12, day=1))
    end_date = fields.Date(required=True, default=fields.Date.context_today)

    def run(self):
        self.ensure_one()
        ppo = self.env['product.product']
        line_obj = self.env['olive.oil.sale.report.line']
        prec = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        if self.start_date.day != 1:
            raise UserError(_(
                "The start date (%s) must be the first day of a month.")
                % format_date(self.env, self.start_date))
        if self.start_date >= self.end_date:
            raise UserError(_(
                "The end date (%(end_date)s) must be after the start date (%(start_date)s).",
                end_date=format_date(self.env, self.end_date),
                start_date=format_date(self.env, self.start_date)))
        oil_product_ids = ppo.with_context(active_test=False).search(
            [('detailed_type', '=', 'olive_oil')]).ids
        bottle2oilandvolume = ppo._get_bottle2oilandvolume()
        # bottle2oilandvolume is for bottles and manufactured pack of bottles
        # {bottle1_id: {oil_product1_id: 0.75, oil_product2_id: 0.75}}
        customer_loc_ids = self.env['stock.location'].search(
            [('usage', '=', 'customer')]).ids
        internal_loc_without_withdrawal_ids = self.company_id._get_internal_locations_without_withdrawal_ids()
        start_date = self.start_date
        end_date = start_date + relativedelta(day=31)
        while start_date <= self.end_date:
            assert start_date.day == 1
            oilproduct2qtydict = {}
            # key = oil_product_id, value = {'loose_qty': 12.0, 'in_bottle_qty'; 5.0}
            for oil_product_id in oil_product_ids:
                oilproduct2qtydict[oil_product_id] = {'loose_qty': 0.0, 'in_bottle_qty': 0.0}
            # Loose
            looseproduct2qty = self._get_product2qty(
                start_date, end_date, oil_product_ids,
                internal_loc_without_withdrawal_ids, customer_loc_ids)
            for oil_product_id, qty in looseproduct2qty.items():
                oilproduct2qtydict[oil_product_id]['loose_qty'] += qty
            # Bottles
            bottleproduct2qty = self._get_product2qty(
                start_date, end_date, list(bottle2oilandvolume),
                internal_loc_without_withdrawal_ids, customer_loc_ids)
            for bottle_product_id, product_qty in bottleproduct2qty.items():
                for oil_product_id, volume in bottle2oilandvolume[bottle_product_id].items():
                    oil_qty = product_qty * volume
                    oilproduct2qtydict[oil_product_id]['in_bottle_qty'] += oil_qty

            # create report lines
            logger.info(
                'Generating %d sale report lines for period %s to %s',
                len(oilproduct2qtydict), start_date, end_date)
            for oil_product_id, qty_dict in oilproduct2qtydict.items():
                if (
                        not float_is_zero(qty_dict['loose_qty'], precision_digits=prec) or
                        not float_is_zero(qty_dict['in_bottle_qty'], precision_digits=prec)):
                    vals = dict(
                        qty_dict, parent_id=self.id, date=start_date,
                        oil_product_id=oil_product_id)
                    vals['total_qty'] = vals['loose_qty'] + vals['in_bottle_qty']
                    # ACL for lines only give read rights, so I use sudo() to create
                    line_obj.sudo().create(vals)
            # next month
            start_date += relativedelta(months=1)
            end_date = start_date + relativedelta(day=31)
        action = self.env['ir.actions.actions']._for_xml_id(
            'olive_mill.olive_oil_sale_report_line_action')
        action['domain'] = [('parent_id', '=', self.id)]
        return action

    def _get_product2qty(
            self, start_date, end_date, product_ids,
            src_location_ids, dest_location_ids):
        self.ensure_one()
        smo = self.env['stock.move']
        res = defaultdict(float)
        move_common_domain = [
            ('state', '=', 'done'),
            ('date', '>=', '%s 00:00:00' % start_date),
            ('date', '<=', '%s 23:59:59' % end_date),
            ('company_id', '=', self.company_id.id),
            ('product_id', 'in', product_ids),
        ]
        move_rg_res = smo.read_group(
            move_common_domain + [
                ('location_id', 'in', src_location_ids),
                ('location_dest_id', 'in', dest_location_ids),
            ], ['product_qty', 'product_id'], ['product_id'])
        for move_rg_re in move_rg_res:
            product_id = move_rg_re['product_id'][0]
            qty = move_rg_re['product_qty']
            res[product_id] += qty
        return_move_rg_res = smo.read_group(
            move_common_domain + [
                ('location_id', 'in', dest_location_ids),
                ('location_dest_id', 'in', src_location_ids),
            ], ['product_qty', 'product_id'], ['product_id'])
        for return_move_rg_re in return_move_rg_res:
            product_id = return_move_rg_re['product_id'][0]
            return_qty = return_move_rg_re['product_qty']
            res[product_id] -= return_qty
        return res


class OliveOilSaleReportLine(models.TransientModel):
    _name = 'olive.oil.sale.report.line'
    _description = 'Olive Oil Sale Report Line'
    _order = "date, oil_product_id"

    parent_id = fields.Many2one('olive.oil.sale.report', ondelete='cascade')
    date = fields.Date(required=True, readonly=True)
    # domain is just to improve usability on search view...
    # but it doesn't seem to work in v14 :-(
    oil_product_id = fields.Many2one(
        'product.product', string='Olive Oil', required=True, readonly=True,
        domain="[('detailed_type', '=', 'olive_oil')]")
    olive_culture_type = fields.Selection(
        related='oil_product_id.olive_culture_type', store=True)
    loose_qty = fields.Float(
        string='Loose Sold Qty (L)', digits='Product Unit of Measure',
        readonly=True)
    in_bottle_qty = fields.Float(
        string='In Bottle Sold Qty (L)', digits='Product Unit of Measure',
        readonly=True)
    total_qty = fields.Float(
        string='Total Sold Qty (L)', digits='Product Unit of Measure',
        readonly=True)
