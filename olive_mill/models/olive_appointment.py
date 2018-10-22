# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta


class OliveAppointment(models.Model):
    _name = 'olive.appointment'
    _description = 'Olive Appointment'
    _order = 'start_datetime desc'
    _inherit = ['mail.thread']

    # name is required when you create from calendar
    # it is also needed for appointments with type = 'other'
    name = fields.Char(string='Note')
    company_id = fields.Many2one(
        'res.company', string='Company',
        ondelete='cascade', required=True,
        default=lambda self: self.env['res.company']._company_default_get(
            'olive.appointment'))
    partner_id = fields.Many2one(
        'res.partner', string='Olive Farmer', required=True, copy=False,
        domain=[('olive_farmer', '=', True)], track_visibility='onchange')
    commercial_partner_id = fields.Many2one(
        related='partner_id.commercial_partner_id', readonly=True, store=True)
    appointment_type = fields.Selection([
        ('lend', 'Lend Palox/Case'),
        ('arrival', 'Arrival'),
        ('withdrawal', 'Withdrawal'),
        ('other', 'Other'),
        ], string='Appointment Type', required=True)
    variant_id = fields.Many2one(
        'olive.variant', string='Olive Variant', track_visibility='onchange')
    leaf_removal = fields.Boolean(
        string='Leaf Removal', track_visibility='onchange')
    qty = fields.Integer(
        string='Quantity', help="Olive quantity in kg",
        track_visibility='onchange')
    start_datetime = fields.Datetime(
        string='Start', required=True, track_visibility='onchange')
    end_datetime = fields.Datetime(
        string='End', required=True)
    oil_destination = fields.Selection([
        ('withdrawal', 'Withdrawal'),
        ('sale', 'Sale'),
        ('mix', 'Mix'),
        ], string='Oil Destination', track_visibility='onchange')
    withdrawal_oil_qty = fields.Integer(
        string='Withdrawal Oil Quantity', track_visibility='onchange')
    palox_qty = fields.Float(
        compute='_compute_palox_qty', string='Estimated Palox Qty', readonly=True,
        store=True)
    arrival_id = fields.Many2one(
        'olive.arrival', 'Olive Arrival', readonly=True, copy=False)

    _sql_constraints = [(
        'qty_positive',
        'CHECK(qty >= 0)',
        'The quantity must be positive or 0.'), (
        'withdrawal_oil_qty_positive',
        'CHECK(withdrawal_oil_qty >= 0)',
        'The quantity of oil withdrawn must be positive or 0.'),
        ]

    @api.onchange('oil_destination')
    def oil_destination_change(self):
        if self.oil_destination in ('sale', 'withdrawal'):
            self.withdrawal_oil_qty = 0

    @api.onchange('partner_id', 'appointment_type')
    def partner_id_change(self):
        if self.partner_id.commercial_partner_id and self.appointment_type == 'arrival':
            ochards = self.env['olive.ochard'].search([
                ('partner_id', '=', self.partner_id.commercial_partner_id.id)])
            if (
                    len(ochards) == 1 and
                    len(ochards[0].parcel_ids) == 1 and
                    len(ochards[0].parcel_ids[0].variant_ids) == 1):
                self.variant_id = ochards[0].parcel_ids[0].variant_ids[0]
        else:
            self.variant_id = False

    @api.depends('partner_id', 'start_datetime')
    def name_get(self):
        res = []
        for app in self:
            start_dt = fields.Datetime.from_string(app.start_datetime)
            start_dt_in_tz = fields.Datetime.context_timestamp(
                self, start_dt)
            start_in_tz = fields.Datetime.to_string(start_dt_in_tz)
            res.append((
                app.id,
                u'%s %s' % (app.partner_id.display_name, start_in_tz[:16])))
        return res

    @api.onchange('start_datetime', 'appointment_type', 'leaf_removal', 'qty')
    def end_datetime_change(self):
        if self.start_datetime and self.appointment_type and self.company_id:
            minutes = False
            company = self.company_id
            start_dt = fields.Datetime.from_string(self.start_datetime)
            if self.appointment_type == 'arrival':
                if self.leaf_removal:
                    duration_coef = company.olive_appointment_arrival_leaf_removal_minutes
                else:
                    duration_coef = company.olive_appointment_arrival_no_leaf_removal_minutes
                minutes = duration_coef * self.qty / 100.0
                if minutes < company.olive_appointment_arrival_min_minutes:
                    minutes = company.olive_appointment_arrival_min_minutes
            elif self.appointment_type == 'lend':
                minutes = company.olive_appointment_lend_minutes
            elif self.appointment_type in ('withdrawal', 'other'):
                minutes = company.olive_appointment_withdrawal_minutes
            if minutes:
                end_dt = start_dt + relativedelta(minutes=minutes)
                self.end_datetime = fields.Datetime.to_string(end_dt)

    @api.depends('qty')
    def _compute_palox_qty(self):
        for app in self:
            palox_qty = 0
            qty_per_palox = app.company_id.olive_appointment_qty_per_palox
            if qty_per_palox:
                palox_qty = app.qty / float(qty_per_palox)
            app.palox_qty = palox_qty

    def create_arrival(self):
        self.ensure_one()
        assert not self.arrival_id
        oao = self.env['olive.arrival']
        vals = {
            'partner_id': self.partner_id.id,
            'company_id': self.company_id.id,
            'default_variant_id': self.variant_id.id or False,
            'default_oil_destination': self.oil_destination,
            'default_leaf_removal': self.leaf_removal,
            }
        vals = oao.play_onchanges(vals, ['partner_id'])
        arrival = oao.create(vals)
        self.arrival_id = arrival.id
        action = self.env['ir.actions.act_window'].for_xml_id(
            'olive_mill', 'olive_arrival_action')
        action.update({
            'res_id': arrival.id,
            'view_mode': 'form,tree',
            'views': False,
            })
        return action
