# -*- coding: utf-8 -*-
# Copyright 2019 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OliveAppointmentPrint(models.TransientModel):
    _name = 'olive.appointment.print'
    _description = 'Wizard to print the appointments of the day'

    date = fields.Date(
        string='Date', default=fields.Date.context_today, required=True)

    def report_get_appointments(self):
        self.ensure_one()
        appointments = self.env['olive.appointment'].search(
            [('date', '=', self.date)], order='start_datetime')
        return appointments

    def run(self):
        self.ensure_one()
        action = self.env['report'].get_action(self, 'olive.appointment.day')
        return action
