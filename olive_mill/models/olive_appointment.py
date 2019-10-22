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
    name = fields.Char(string='Notes')
    company_id = fields.Many2one(
        'res.company', string='Company',
        ondelete='cascade', required=True,
        default=lambda self: self.env['res.company']._company_default_get())
    season_id = fields.Many2one(
        'olive.season', string='Season', required=True, index=True,
        default=lambda self: self.env.user.company_id.current_season_id.id)
    partner_id = fields.Many2one(
        'res.partner', string='Olive Farmer', required=True, copy=False,
        domain=[('olive_farmer', '=', True)], track_visibility='onchange')
    commercial_partner_id = fields.Many2one(
        related='partner_id.commercial_partner_id', readonly=True, store=True)
    olive_cultivation_form_ko = fields.Boolean(
        related='partner_id.commercial_partner_id.olive_cultivation_form_ko',
        readonly=True)
    olive_parcel_ko = fields.Boolean(
        related='partner_id.commercial_partner_id.olive_parcel_ko', readonly=True)
    olive_organic_certif_ko = fields.Boolean(
        related='partner_id.commercial_partner_id.olive_organic_certif_ko',
        readonly=True)
    olive_invoicing_ko = fields.Boolean(
        related='partner_id.commercial_partner_id.olive_invoicing_ko',
        readonly=True)
    olive_culture_type = fields.Selection(
        related='partner_id.commercial_partner_id.olive_culture_type',
        readonly=True)
    olive_organic_certified_logo = fields.Binary(
        related='partner_id.commercial_partner_id.olive_organic_certified_logo',
        readonly=True)
    appointment_type = fields.Selection([
        ('lend', 'Lend Palox/Cases'),
        ('arrival', 'Arrival'),
        ('withdrawal', 'Withdrawal'),
        ('other', 'Other'),
        ], string='Appointment Type', required=True)
    withdrawal_invoice = fields.Selection([
        ('invoice', 'With Invoice'),
        ('noinvoice', 'Without Invoice'),
        ], string='Invoicing')
    lend_palox_qty = fields.Integer(string='Number of Palox')
    lend_regular_case_qty = fields.Integer(string='Number of Regular Cases')
    lend_organic_case_qty = fields.Integer(string='Number of Organic Cases')
    variant_id = fields.Many2one(
        'olive.variant', string='Olive Variant', track_visibility='onchange')
    leaf_removal = fields.Boolean(
        string='Leaf Removal', track_visibility='onchange')
    oil_product_id = fields.Many2one(
        'product.product', string='Oil Type',
        domain=[('olive_type', '=', 'oil')])
    qty = fields.Integer(
        string='Quantity', help="Olive quantity in kg",
        track_visibility='onchange')
    start_datetime = fields.Datetime(
        string='Start', required=True, track_visibility='onchange')
    end_datetime = fields.Datetime(string='End', required=True)
    date = fields.Date(
        compute='_compute_date', string='Date', store=True, readonly=True)
    oil_destination = fields.Selection([
        ('withdrawal', 'Withdrawal'),
        ('sale', 'Sale'),
        ('mix', 'Mix'),
        ], string='Oil Destination', track_visibility='onchange')
    withdrawal_oil_qty = fields.Integer(
        string='Withdrawal Oil Quantity', track_visibility='onchange')
    palox_qty = fields.Float(
        compute='_compute_palox_qty', string='Estimated Palox Qty', readonly=True,
        store=True, digits=(16, 1))
    total_qty_same_day = fields.Integer(
        compute='_compute_total_qty_same_day',
        string='Total Olive Arrival Same Day', readonly=True,
        help="Total qty of olive arrival on the same day, including this appointment.")
    total_palox_same_day = fields.Float(
        compute='_compute_total_qty_same_day',
        string='Total Palox Same Day', readonly=True, digits=(16, 1),
        help="Total qty of olive arrival on the same day, including this appointment.")
    display_calendar_label = fields.Char(
        compute='_compute_display_calendar_label',
        string='Label in Calendar View', readonly=True)

    _sql_constraints = [(
        'qty_positive',
        'CHECK(qty >= 0)',
        'The quantity must be positive or null.'), (
        'withdrawal_oil_qty_positive',
        'CHECK(withdrawal_oil_qty >= 0)',
        'The quantity of oil withdrawn must be positive or null.'),
        ]

    @api.depends('start_datetime')
    def _compute_date(self):
        # TODO add support for TZ
        for app in self:
            app.date = app.start_datetime and app.start_datetime[:10] or False

    @api.depends('start_datetime', 'qty', 'palox_qty')
    def _compute_total_qty_same_day(self):
        for app in self:
            total_qty_same_day = 0
            total_palox_same_day = 0.0
            if app.start_datetime:
                rg_res = self.read_group([
                    ('date', '=', app.start_datetime[:10]),
                    ('appointment_type', '=', 'arrival')], ['qty', 'palox_qty'], [])
                total_qty_same_day = rg_res and rg_res[0]['qty'] or 0
                total_palox_same_day = rg_res and rg_res[0]['palox_qty'] or 0
            app.total_qty_same_day = total_qty_same_day
            app.total_palox_same_day = total_palox_same_day

    @api.depends(
        'partner_id', 'appointment_type', 'qty', 'oil_destination',
        'withdrawal_oil_qty',
        'oil_product_id', 'leaf_removal', 'withdrawal_invoice',
        'lend_palox_qty', 'lend_regular_case_qty', 'lend_organic_case_qty')
    def _compute_display_calendar_label(self):
        for app in self:
            label = app.partner_id.name
            if app.olive_culture_type and app.olive_culture_type != 'regular':
                olive_culture_type_label = dict(app.fields_get('olive_culture_type', 'selection')['olive_culture_type']['selection'])[app.olive_culture_type]
                label += ' [%s]' % olive_culture_type_label
            if app.appointment_type == 'arrival':
                label += ', %d kg' % app.qty
                if app.oil_destination == 'withdrawal':
                    label += _(' (Withdrawal)')
                elif app.oil_destination == 'mix':
                    label += _(' (Partial withdrawal: %d L)') % app.withdrawal_oil_qty
                if app.oil_product_id:
                    label += ', %s' % app.oil_product_id.name
                if app.leaf_removal:
                    label += _(', LEAF REMOVAL')
            elif app.appointment_type == 'withdrawal':
                invoicing_label = dict(app.fields_get('withdrawal_invoice', 'selection')['withdrawal_invoice']['selection'])[app.withdrawal_invoice]
                label += ', %s' % invoicing_label
            elif app.appointment_type == 'lend':
                lend_list = []
                if app.lend_palox_qty:
                    lend_list.append(_('Palox: %d') % app.lend_palox_qty)
                if app.lend_regular_case_qty:
                    lend_list.append(_('Regular cases: %d') % app.lend_regular_case_qty)
                if app.lend_organic_case_qty:
                    lend_list.append(_('Organic cases: %d') % app.lend_organic_case_qty)
                if lend_list:
                    label += ', %s' % ', '.join(lend_list)
            app.display_calendar_label = label

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
            self.qty = False

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
            palox_qty = 0.0
            qty_per_palox = app.company_id.olive_appointment_qty_per_palox
            if qty_per_palox:
                palox_qty = app.qty / float(qty_per_palox)
            app.palox_qty = round(palox_qty, 1)

    def open_arrival(self):
        self.ensure_one()
        context = {
            'default_partner_id': self.commercial_partner_id.id,
            'default_company_id': self.company_id.id,
            'default_default_variant_id': self.variant_id.id or False,
            'default_default_oil_destination': self.oil_destination,
            'default_default_leaf_removal': self.leaf_removal,
            'default_default_oil_product_id': self.oil_product_id.id or False,
            }
        action = self.env['ir.actions.act_window'].for_xml_id(
            'olive_mill', 'olive_arrival_action')
        action.update({
            'view_mode': 'form,tree',
            'views': False,
            'context': context,
            })
        return action

    def open_new_appointment(self):
        self.ensure_one()
        context = {
            'default_partner_id': self.partner_id.id,
            'default_company_id': self.company_id.id,
            'default_appointment_type': self.appointment_type,
            'default_variant_id': self.variant_id.id or False,
            'default_oil_destination': self.oil_destination,
            'default_leaf_removal': self.leaf_removal,
            'default_oil_product_id': self.oil_product_id.id or False,
            'default_qty': self.qty,
            'default_withdrawal_oil_qty': self.withdrawal_oil_qty,
            }
        action = self.env['ir.actions.act_window'].for_xml_id(
            'olive_mill', 'olive_appointment_action')
        action.update({
            'view_mode': 'form,tree,calendar',
            'views': False,
            'context': context,
            })
        return action

    def report_show_timeslot(self):
        # show timeslot in right TZ
        self.ensure_one()
        start_datetime_tz = fields.Datetime.context_timestamp(
            self, fields.Datetime.from_string(self.start_datetime))
        end_datetime_tz = fields.Datetime.context_timestamp(
            self, fields.Datetime.from_string(self.end_datetime))
        label = '%s - %s' % (
            fields.Datetime.to_string(start_datetime_tz)[11:16],
            fields.Datetime.to_string(end_datetime_tz)[11:16])
        return label

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(OliveAppointment, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        return self.env.user.company_id.current_season_update(res, view_type)
