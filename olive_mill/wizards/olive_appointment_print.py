# Copyright 2019-2023 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OliveAppointmentPrint(models.TransientModel):
    _name = 'olive.appointment.print'
    _description = 'Wizard to print the appointments of the day'

    company_id = fields.Many2one(
        'res.company', ondelete='cascade', required=True,
        default=lambda self: self.env.company)
    date = fields.Date(
        string='Date', default=fields.Date.context_today, required=True)

    def report_get_appointments(self):
        self.ensure_one()
        appointments = self.env['olive.appointment'].search(
            [('date', '=', self.date), ('company_id', '=', self.company_id.id)], order='start_datetime')
        return appointments
