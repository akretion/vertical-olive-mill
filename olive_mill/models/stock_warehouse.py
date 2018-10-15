# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
import odoo.addons.decimal_precision as dp
from dateutil.relativedelta import relativedelta
import logging
logger = logging.getLogger(__name__)


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    olive_mill = fields.Boolean(string='Olive Mill')
    olive_shrinkage_loc_id = fields.Many2one(
        'stock.location', string='Olive Oil Shrinkage Tank',
        domain=[('olive_tank', '=', True)])
    olive_withdrawal_loc_id = fields.Many2one(
        'stock.location', string='Olive Oil Withdrawal Location',
        domain=[('olive_tank', '=', False), ('usage', '=', 'internal')])
    olive_oil_compensation_olive_qty = fields.Float(
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
        'Oil compensation ratio must be positive or 0'),
        ('olive_oil_compensation_olive_qty',
         'CHECK(olive_oil_compensation_olive_qty) >= 0)',
         'Olive Compensation Quantity must be positive or 0')]

    @api.model
    def olive_oil_compensation_ratio_update_cron(self):
        logger.info('Starting oil compensation ratio update cron')
        for wh in self.search([('olive_mill', '=', True)]):
            wh.olive_oil_compensation_ratio_update()

    def olive_oil_compensation_ratio_update(self):
        oalo = self.env['olive.arrival.line']
        today = fields.Date.context_today(self)
        today_dt = fields.Date.from_string(today)
        if not self.olive_mill:
            return
        start_date_dt = today_dt - relativedelta(
            days=self.olive_oil_compensation_ratio_days)
        start_date = fields.Date.to_string(start_date_dt)
        rg = oalo.read_group([
            ('production_state', '=', 'done'),
            ('production_date', '<=', today),
            ('production_date', '>=', start_date),
            ], ['olive_qty', 'oil_qty'], [])
        if rg[0]['olive_qty']:
            ratio = 100 * rg[0]['oil_qty'] / rg[0]['olive_qty']
        self.write({
            'olive_oil_compensation_ratio_update_date': today,
            'olive_oil_compensation_ratio': ratio,
            })
        logger.info(
            'Oil compensation ratio updated to %s on warehouse %s '
            'start_date %s ', ratio, self.name, start_date)
