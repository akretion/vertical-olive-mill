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

    company_id = fields.Many2one(
        'res.company', string='Company',
        ondelete='cascade', required=True,
        default=lambda self: self.env['res.company']._company_default_get(
            'olive.appointment'))
    partner_id = fields.Many2one(
        'res.partner', string='Olive Farmer', required=True, copy=False,
        domain=[('parent_id', '=', False), ('olive_farmer', '=', True)],
        track_visibility='onchange')
    product_id = fields.Many2one(
        'product.product', string='Olive Type',
        domain=[('olive_type', '=', 'olive')], track_visibility='onchange')
    leaf_removal = fields.Boolean(
        string='Leaf Removal', track_visibility='onchange')
    qty = fields.Integer(
        string='Quantity', help="Olive quantity in kg",
        track_visibility='onchange')
    start_datetime = fields.Datetime(
        string='Start', required=True, track_visibility='onchange')
    end_datetime = fields.Datetime(
        string='End', compute='_compute_end_datetime', readonly=True)
    oil_destination = fields.Selection([
        ('withdrawal', 'Withdrawal'),
        ('sale', 'Sale'),
        ('mix', 'Mix'),
        ], string='Oil Destination', track_visibility='onchange')
    sale_qty = fields.Integer(
        string='Sale Quantity', track_visibility='onchange')
    palox_qty = fields.Float(
        compute='_compute_palox_qty', string='Estimated Palox Qty', readonly=True,
        store=True)
    arrival_id = fields.Many2one(
        'olive.arrival', 'Olive Arrival', readonly=True, copy=False)

    _sql_constraints = [(
        'qty_positive',
        'CHECK(qty >= 0)',
        'The quantity must be positive or 0.'), (
        'purchase_qty_positive',
        'CHECK(purchase_qty >= 0)',
        'The purchase quantity must be positive or 0.'),
        ]

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

    @api.depends('start_datetime', 'leaf_removal', 'qty')
    def _compute_end_datetime(self):
        for app in self:
            if app.start_datetime and app.qty:
                start_dt = fields.Datetime.from_string(app.start_datetime)
                if app.leaf_removal:
                    duration_coef = app.company_id.olive_appointment_leaf_removal_minutes
                else:
                    duration_coef = app.company_id.olive_appointment_no_leaf_removal_minutes
                minutes = duration_coef * app.qty / 100.0
                end_dt = start_dt + relativedelta(minutes=minutes)
                app.end_datetime = fields.Datetime.to_string(end_dt)
            else:
                app.end_datetime = False

    @api.depends('qty')
    def _compute_palox_qty(self):
        for app in self:
            palox_qty = 0
            if app.company_id.olive_qty_per_palox:
                palox_qty = app.qty / float(app.company_id.olive_qty_per_palox)
            app.palox_qty = palox_qty

    def create_arrival(self):
        self.ensure_one()
        assert not self.arrival_id
        vals = {
            'partner_id': self.partner_id.id,
            'company_id': self.company_id.id,
            'default_product_id': self.product_id.id or False,
            'default_oil_destination': self.oil_destination,
            'leaf_removal': self.leaf_removal,
            }
        ochards = self.env['stock.location'].search([
            ('partner_id', '=', self.partner_id.id),
            ('olive_type', '=', 'ochard'),
            ])
        if len(ochards) == 1:
            vals['default_src_location_id'] = ochards[0].id
        arrival = self.env['olive.arrival'].create(vals)
        self.arrival_id = arrival.id
        action = self.env['ir.actions.act_window'].for_xml_id(
            'olive_mill', 'olive_arrival_action')
        action.update({
            'res_id': arrival.id,
            'view_mode': 'form,tree',
            'views': False,
            })
        return action
