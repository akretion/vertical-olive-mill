# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, fields, _
from odoo.exceptions import ValidationError
import odoo.addons.decimal_precision as dp


class OlivePalox(models.Model):
    _name = 'olive.palox'
    _description = 'Olive Palox'
    _order = 'name'

    name = fields.Char(string='Number', required=True)
    label = fields.Char(string='Label')
    company_id = fields.Many2one(
        'res.company', string='Company', ondelete='cascade', required=True,
        default=lambda self: self.env['res.company']._company_default_get(
            'olive.palox'))
    borrower_partner_id = fields.Many2one(
        'res.partner', string='Borrower', ondelete='restrict', copy=False,
        domain=[('parent_id', '=', False), ('olive_farmer', '=', True)])
    borrowed_date = fields.Date('Borrowed Date')
    active = fields.Boolean(default=True)
    production_ids = fields.One2many(
        'olive.oil.production', 'palox_id', string='Oil Productions')
    arrival_line_ids = fields.One2many(
        'olive.arrival.line', 'palox_id', string='Arrival Lines')
    # ??? fillup_ok = fields.Boolean(compute='_compute_weight')
    oil_product_id = fields.Many2one(
        'product.product', string='Current Oil Product')
    weight = fields.Float(
        compute='_compute_weight', string='Current Weight (kg)',
        digits=dp.get_precision('Olive Weight'), readonly=True)
    oil_destination = fields.Selection([
        ('withdrawal', 'Withdrawal'),
        ('sale', 'Sale'),
        ('mix', 'Mix'),
        ], string='Oil Destination', compute='_compute_other',
        readonly=True)
    farmers = fields.Char(
        string='Farmers', compute='_compute_other', readonly=True)
    line_ids = fields.One2many(
        'olive.arrival.line', 'palox_id', string='Content', readonly=True,
        domain=[('state', '=', 'done'), ('production_id', '=', False)])

    def _compute_weight(self):
        res = self.env['olive.arrival.line'].read_group([
            ('palox_id', 'in', self.ids),
            ('state', '=', 'done'),
            ('production_id', '=', False),
            ], ['palox_id', 'olive_qty'], ['palox_id'])
        for re in res:
            self.browse(re['palox_id'][0]).weight = re['olive_qty']

    # I don't put the 2 compute methods in the same,
    # because name_get() only uses weight, and computation of weight is
    # fast with read_group()
    def _compute_other(self):
        lines = self.env['olive.arrival.line'].search([
            ('palox_id', 'in', self.ids),
            ('state', '=', 'done'),
            ('production_id', '=', False),
            ])
        paloxes = {}
        for l in lines:
            if l.palox_id not in paloxes:
                paloxes[l.palox_id] = {
                    'oil_dests': [l.oil_destination],
                    'farmers': [l.commercial_partner_id.name],
                    }
            else:
                paloxes[l.palox_id]['oil_dests'].append(l.oil_destination)
                paloxes[l.palox_id]['farmers'].append(l.commercial_partner_id.name)
        for palox, rdict in paloxes.iteritems():
            oil_destination = 'mix'
            if all([dest == 'sale' for dest in rdict['oil_dests']]):
                oil_destination = 'sale'
            elif all([dest == 'withdrawal' for dest in rdict['oil_dests']]):
                oil_destination = 'withdrawal'
            palox.oil_destination = oil_destination
            palox.farmers = u' / '.join(rdict['farmers'])

    @api.constrains('borrower_partner_id', 'borrowed_date')
    def palox_check(self):
        for palox in self:
            if (
                    (palox.borrower_partner_id and not palox.borrowed_date) or
                    (not palox.borrower_partner_id and palox.borrowed_date)):
                raise ValidationError(_(
                    "On palox %s, the fields 'Borrower' and 'Borrowed Date' "
                    "should be either both set or both empty.") % palox.name)

    def name_get(self):
        res = []
        for rec in self:
            label = rec.label and ' ' + rec.label or ''
            name = _('%s%s (Current: %s kg%s)') % (rec.name, label, rec.weight, rec.oil_product_id and ' ' + rec.oil_product_id.name or '')
            res.append((rec.id, name))
        return res

    _sql_constraints = [(
        'name_company_unique',
        'unique(name, company_id)',
        'This palox number already exists in this company.')]
