# -*- coding: utf-8 -*-
# Copyright 2019 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, _
from datetime import datetime
from dateutil.relativedelta import relativedelta


class OliveOilProductionDayPrint(models.TransientModel):
    _name = 'olive.oil.production.day.print'
    _description = 'Wizard to print the olive oil productions of the day'

    date = fields.Date(
        string='Date', default=fields.Date.context_today, required=True)

    def report_get_line_details(self):
        self.ensure_one()
        prods = self.env['olive.oil.production'].search(
            [('date', '=', self.date), ('state', '!=', 'cancel')], order='sequence desc, id asc')
        res = []
        i = 0
        company = self.env.user.company_id
        start_time_str = '%s:%s' % (
            company.olive_oil_production_start_hour,
            company.olive_oil_production_start_minute)
        datetime_dt = datetime.strptime(start_time_str, '%H:%M')
        for prod in prods:
            i += 1
            hour_label = datetime_dt.strftime(_('%H:%M'))
            res.append({
                'prod': prod,
                'order': str(i),
                'hour': hour_label,
                })
            datetime_dt += relativedelta(minutes=company.olive_oil_production_duration_minutes)
        return res

    def run(self):
        self.ensure_one()
        action = self.env['report'].get_action(self, 'olive.oil.production.day')
        return action
