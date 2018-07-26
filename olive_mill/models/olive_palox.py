# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, fields


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

    _sql_constraints = [(
        'number_company_unique',
        'unique(number, company_id)',
        'This palox number already exists in this company.')]
