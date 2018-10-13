# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, fields, _
import odoo.addons.decimal_precision as dp


class OlivePalox(models.Model):
    _name = 'olive.palox'
    _description = 'Olive Palox'
    _inherit = ['mail.thread']
    _rec_name = 'number'
    _order = 'number'

    number = fields.Char(
        string='Number', required=True, track_visibility='onchange')
    company_id = fields.Many2one(
        'res.company', string='Company', ondelete='cascade', required=True,
        default=lambda self: self.env['res.company']._company_default_get(
            'olive.palox'))
    organic = fields.Boolean(string='Organic')
    borrower_partner_id = fields.Many2one(
        'res.partner', string='Borrower', ondelete='restrict', copy=False,
        domain=[('parent_id', '=', False), ('olive_farmer', '=', True)],
        track_visibility='onchange')
    borrowed_date = fields.Date('Borrowed Date', track_visibility='onchange')
    active = fields.Boolean(default=True)
    production_ids = fields.One2many(
        'olive.oil.production', 'palox_id', string='Oil Productions')
    arrival_line_ids = fields.One2many(
        'olive.arrival.line', 'palox_id', string='Arrival Lines')
    fillup_ok = fields.Boolean(compute='_compute_weight')
    weight = fields.Float(
        compute='_compute_weight', string='Current Weight (kg)',
        digits=dp.get_precision('Olive Weight'), readonly=True)

    def _compute_weight(self):
        res = self.env['olive.arrival.line'].read_group([
            ('palox_id', 'in', self.ids),
            ('arrival_state', '=', 'done'),
            ('production_state', 'not in', ('done', 'cancel')),
            ], ['palox_id', 'olive_qty'], ['palox_id'])
        for re in res:
            self.browse(re['palox_id'][0]).weight = re['olive_qty']

    def name_get(self):
        res = []
        for rec in self:
            name = _('%s (Current: %s kg)') % (rec.number, rec.weight)
            res.append((rec.id, name))
        return res

    _sql_constraints = [(
        'number_company_unique',
        'unique(number, company_id)',
        'This palox number already exists in this company.')]
