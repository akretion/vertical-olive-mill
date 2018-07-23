# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _



class OliveAppointment(models.Model):
    _name = 'olive.appointment'
    _description = 'Olive Appointment'
    _inherit = ['mail.thread']

    company_id = fields.Many2one(
        'res.company', string='Company',
        ondelete='cascade', required=True,
        default=lambda self: self.env['res.company']._company_default_get(
            'olive.appointment'))
    partner_id = fields.Many2one(
        'res.partner', string='Borrower', required=True, copy=False,
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
        string='End', required=True, track_visibility='onchange')
    oil_destination = fields.Selection([
        ('withdrawal', 'Withdrawal'),
        ('purchase', 'Purchase'),
        ('mix', 'Mix'),
        ], string='Oil Destination')
    purchase_qty = fields.Integer(string='Purchase Quantity')
    palox_qty = fields.Float(
        compute='_compute_palox_qty', string='Estimated Palox Qty', readonly=True,
        store=True)

    _sql_constraints = [(
        'qty_positive',
        'CHECK(qty >= 0)',
        'The quantity must be positive of 0.'), (
        'purchase_qty_positive',
        'CHECK(purchase_qty >= 0)',
        'The purchase quantity must be positive of 0.'),
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

    @api.depends('qty')
    def _compute_palox_qty(self):
        for app in self:
            palox_qty = 0
            print "app.company_id=", app.company_id
            print "app.company_id.olive_qty_per_palox:=", app.company_id.olive_qty_per_palox
            if app.company_id.olive_qty_per_palox:
                palox_qty = app.qty / float(app.company_id.olive_qty_per_palox)
            app.palox_qty = palox_qty
