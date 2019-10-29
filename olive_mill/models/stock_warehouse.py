# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
import logging
logger = logging.getLogger(__name__)


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    olive_mill = fields.Boolean(string='Olive Mill')
    olive_regular_case_total = fields.Integer(string='Regular Cases Total')
    olive_regular_case_stock = fields.Integer(
        compute='_compute_cases', string='Regular Cases in Stock',
        readonly=True)
    olive_organic_case_total = fields.Integer(string='Organic Cases Total')
    olive_organic_case_stock = fields.Integer(
        compute='_compute_cases', string='Organic Cases in Stock',
        readonly=True)
    olive_withdrawal_loc_id = fields.Many2one(
        'stock.location', string='Olive Oil Withdrawal Location',
        domain=[('olive_tank_type', '=', False), ('usage', '=', 'internal')])
    olive_compensation_loc_id = fields.Many2one(
        'stock.location', string='Olive Oil Compensation Tank',
        domain=[('olive_tank_type', '=', 'compensation')])
    olive_compensation_last_qty = fields.Float(
        string='Olive Compensation Quantity', default=45.0,
        digits=dp.get_precision('Olive Weight'))
    olive_oil_compensation_ratio = fields.Float(
        string='Compensation Ratio',
        digits=dp.get_precision('Olive Oil Ratio'), default=17)
    olive_oil_compensation_ratio_update_date = fields.Date(
        string='Last Update of the Compensation Ratio')
    olive_oil_compensation_ratio_days = fields.Integer(
        string='Base for Compensation Ratio Computation', default=7)

    _sql_constraints = [(
        'olive_oil_compensation_ratio_positive',
        'CHECK(olive_oil_compensation_ratio >= 0)',
        'Oil compensation ratio must be positive or null.'),
        ('olive_compensation_last_qty_positive',
         'CHECK(olive_compensation_last_qty >= 0)',
         'Olive Compensation Quantity must be positive or null.')]

    @api.depends('olive_organic_case_total', 'olive_regular_case_total')
    def _compute_cases(self):
        cases_res = self.env['olive.lended.case'].read_group(
            [('warehouse_id', 'in', self.ids)],
            ['warehouse_id', 'regular_qty', 'organic_qty'], ['warehouse_id'])
        if cases_res:
            for cases_re in cases_res:
                wh = self.browse(cases_re['warehouse_id'][0])
                wh.olive_regular_case_stock =\
                    wh.olive_regular_case_total - cases_re['regular_qty']
                wh.olive_organic_case_stock =\
                    wh.olive_organic_case_total - cases_re['organic_qty']
        else:
            for wh in self:
                wh.olive_regular_case_stock = wh.olive_regular_case_total
                wh.olive_organic_case_stock = wh.olive_organic_case_total

    @api.model
    def olive_oil_compensation_ratio_update_cron(self):
        logger.info('Starting oil compensation ratio update cron')
        for wh in self.search([('olive_mill', '=', True)]):
            wh.olive_oil_compensation_ratio_update()

    def olive_oil_compensation_ratio_update(self):
        today = fields.Date.context_today(self)
        today_dt = fields.Date.from_string(today)
        if not self.olive_mill:
            return
        start_date_dt = today_dt - relativedelta(
            days=self.olive_oil_compensation_ratio_days)
        start_date = fields.Date.to_string(start_date_dt)
        rg = self.env['olive.arrival.line'].read_group([
            ('production_state', '=', 'done'),
            ('production_date', '<=', today),
            ('production_date', '>=', start_date),
            ], ['olive_qty', 'oil_qty'], [])
        if rg and rg[0]['olive_qty']:
            ratio = 100 * rg[0]['oil_qty'] / rg[0]['olive_qty']
            self.write({
                'olive_oil_compensation_ratio_update_date': today,
                'olive_oil_compensation_ratio': ratio,
                })
            logger.info(
                'Oil compensation ratio updated to %s on warehouse %s '
                'start_date %s ', ratio, self.name, start_date)
        else:
            logger.warning(
                'Oil compensation ratio not updated on warehouse %s '
                'because there is no production data between %s and %s',
                self.name, start_date, today)

    def olive_get_shrinkage_tank(self, oil_product, raise_if_not_found=True):
        self.ensure_one()
        assert oil_product, 'oil_product is a required arg'
        sloc = self.env['stock.location'].search([
            ('olive_tank_type', '=', 'shrinkage'),
            ('id', 'child_of', self.view_location_id.id),
            ('olive_shrinkage_oil_product_ids', '=', oil_product.id)],
            limit=1)
        if not sloc and raise_if_not_found:
            raise UserError(_(
                "Could not find a shrinkage tank in warehouse '%s' "
                "that accepts '%s'.") % (
                    self.display_name, oil_product.name))
        return sloc or False
