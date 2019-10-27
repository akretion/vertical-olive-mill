# -*- coding: utf-8 -*-
# Copyright 2019 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime
from dateutil.relativedelta import relativedelta


class OliveOilProductionDayPrint(models.TransientModel):
    _name = 'olive.oil.production.day.print'
    _description = 'Wizard to print the olive oil productions of the day'

    @api.model
    def default_get(self, fields_list):
        res = super(OliveOilProductionDayPrint, self).default_get(fields_list)
        company = self.env.user.company_id
        res.update({
            'start_hour': company.olive_oil_production_start_hour,
            'start_minute': company.olive_oil_production_start_minute,
            'duration_minutes': company.olive_oil_production_duration_minutes,
            })
        return res

    date = fields.Date(
        string='Date', default=fields.Date.context_today, required=True)
    start_hour = fields.Integer(string='Start Hour', required=True)
    start_minute = fields.Integer(string='Start Minute', required=True)
    duration_minutes = fields.Integer(
        string='Duration of one Oil Production', required=True)

    _sql_constraints = [(
        'duration_minutes_positive',
        'CHECK(duration_minutes >= 0)',
        'Duration must be positive.')]

    def report_get_line_details(self):
        self.ensure_one()
        prods = self.env['olive.oil.production'].search(
            [('date', '=', self.date), ('state', '!=', 'cancel')], order='sequence desc, id asc')
        res = []
        i = 0
        start_time_str = '%s:%s' % (self.start_hour, self.start_minute)
        try:
            datetime_dt = datetime.strptime(start_time_str, '%H:%M')
        except ValueError:
            raise UserError(_(
                "Start hour (%s) and/or start minute (%s) contain invalid values.")
                % (self.start_hour, self.start_minute))
        for prod in prods:
            i += 1
            hour_label = datetime_dt.strftime(_('%H:%M'))
            res.append({
                'prod': prod,
                'order': str(i),
                'hour': hour_label,
                })
            datetime_dt += relativedelta(minutes=self.duration_minutes)
        return res

    def run(self):
        self.ensure_one()
        action = self.env['report'].get_action(self, 'olive.oil.production.day')
        return action
