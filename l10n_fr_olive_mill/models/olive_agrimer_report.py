# -*- coding: utf-8 -*-
# Copyright 2019 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError


class OliveAgrimerReport(models.Model):
    _name = 'olive.agrimer.report'
    _inherit = ['mail.thread']
    _description = 'Olive ARGIMER reports'
    _order = 'date_start desc'
    _rec_name = 'date_start'

    company_id = fields.Many2one(
        'res.company', string='Company',
        ondelete='cascade', required=True,
        states={'done': [('readonly', True)]},
        default=lambda self: self.env['res.company']._company_default_get())
    date_range_id = fields.Many2one(
        'date.range', string='Date Range',
        states={'done': [('readonly', True)]})
    date_start = fields.Date(
        string='Start Date', required=True, track_visibility='onchange',
        states={'done': [('readonly', True)]})
    date_end = fields.Date(
        string='End Date', track_visibility='onchange',
        required=True, states={'done': [('readonly', True)]})
    olive_arrival_qty = fields.Float(
        string='Olive Arrival (kg)', digits=dp.get_precision('Olive Weight'),
        states={'done': [('readonly', True)]})
    olive_pressed_qty = fields.Float(
        string='Olive Pressed (kg)', digits=dp.get_precision('Olive Weight'),
        states={'done': [('readonly', True)]})
    organic_virgin_oil_produced = fields.Float(
        string='Organic Virgin Olive Oil Produced (L)',
        digits=dp.get_precision('Olive Oil Volume'),
        states={'done': [('readonly', True)]})
    organic_extravirgin_oil_produced = fields.Float(
        string='Organic Extra Virgin Olive Oil Produced (L)',
        digits=dp.get_precision('Olive Oil Volume'),
        states={'done': [('readonly', True)]})
    regular_virgin_oil_produced = fields.Float(
        string='Regular Virgin Olive Oil Produced (L)',
        digits=dp.get_precision('Olive Oil Volume'),
        states={'done': [('readonly', True)]})
    regular_extravirgin_oil_produced = fields.Float(
        string='Regular Extra Virgin Olive Oil Produced (L)',
        digits=dp.get_precision('Olive Oil Volume'),
        states={'done': [('readonly', True)]})
    shrinkage_organic_virgin_oil = fields.Float(
        string='Shrinkage Organic Virgin Oil (L)',
        digits=dp.get_precision('Olive Oil Volume'),
        states={'done': [('readonly', True)]})
    shrinkage_organic_extravirgin_oil = fields.Float(
        string='Shrinkage Organic Extra Virgin Oil (L)',
        digits=dp.get_precision('Olive Oil Volume'),
        states={'done': [('readonly', True)]})
    shrinkage_regular_virgin_oil = fields.Float(
        string='Shrinkage Regular Virgin Oil (L)',
        digits=dp.get_precision('Olive Oil Volume'),
        states={'done': [('readonly', True)]})
    shrinkage_regular_extravirgin_oil = fields.Float(
        string='Shrinkage Regular Extra Virgin Oil (L)',
        digits=dp.get_precision('Olive Oil Volume'),
        states={'done': [('readonly', True)]})

    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ], default='draft', readonly=True, track_visibility='onchange')

    _sql_constraints = [(
        'date_company_uniq',
        'unique(date_start, company_id)',
        'A DEB of the same type already exists for this month !')]

    @api.onchange('date_range_id')
    def onchange_date_range_id(self):
        if self.date_range_id:
            self.date_start = self.date_range_id.date_start
            self.date_end = self.date_range_id.date_end

    def draft2done(self):
        self.ensure_one()
        assert self.state == 'draft'
        self.state = 'done'

    def back2draft(self):
        self.ensure_one()
        assert self.state == 'done'
        self.state = 'draft'

    def _compute_olive_arrival_qty(self, vals):
        rg = self.env['olive.arrival.line'].read_group([
            ('arrival_date', '>=', self.date_start),
            ('arrival_date', '<=', self.date_end),
            ('arrival_state', '=', 'done'),
            ], ['olive_qty'], [])
        vals['olive_arrival_qty'] = rg and rg[0]['olive_qty'] or 0.0

    def _compute_olive_pressed_qty(self, vals):
        rg = self.env['olive.arrival.line'].read_group([
            ('production_date', '>=', self.date_start),
            ('production_date', '<=', self.date_end),
            ('production_state', '=', 'done'),
            ], ['olive_qty'], [])
        vals['olive_pressed_qty'] = rg and rg[0]['olive_qty'] or 0.0

    def _compute_oil_produced(self, vals, oil_product_domain):
        ppo = self.env['product.product']
        for field_prefix, pdomain in oil_product_domain.items():
            net_fieldname = '%s_oil_produced' % field_prefix
            shrinkage_fieldname = 'shrinkage_%s_oil' % field_prefix
            oil_products = ppo.search(pdomain)
            rg = self.env['olive.arrival.line'].read_group([
                ('oil_product_id', 'in', oil_products.ids),
                ('production_date', '>=', self.date_start),
                ('production_date', '<=', self.date_end),
                ('production_state', '=', 'done'),
                ], ['oil_qty_net', 'shrinkage_oil_qty'], [])
            vals[net_fieldname] = rg and rg[0]['oil_qty_net'] or 0.0
            vals[shrinkage_fieldname] =\
                rg and rg[0]['shrinkage_oil_qty'] or 0.0

    def report_compute_values(self):
        oil_product_domain = {
            'organic_virgin': [
                ('olive_type', '=', 'oil'),
                ('olive_oil_type', '=', 'virgin'),
                ('olive_culture_type', '=', 'organic')],
            'organic_extravirgin': [
                ('olive_type', '=', 'oil'),
                ('olive_oil_type', '=', 'extravirgin'),
                ('olive_culture_type', '=', 'organic')],
            'regular_virgin': [
                ('olive_type', '=', 'oil'),
                ('olive_oil_type', '=', 'virgin'),
                ('olive_culture_type', '!=', 'organic')],
            'regular_extravirgin': [
                ('olive_type', '=', 'oil'),
                ('olive_oil_type', '=', 'extravirgin'),
                ('olive_culture_type', '!=', 'organic')],
            }
        vals = {}
        self._compute_olive_arrival_qty(vals)
        self._compute_olive_pressed_qty(vals)
        self._compute_oil_produced(vals, oil_product_domain)
        return vals

    def generate_report(self):
        vals = self.report_compute_values()
        self.write(vals)
        self.message_post(_("AgriMer report generated."))

    def olive_stock_levels(self, vals):
        vals['olive_stock_start']
