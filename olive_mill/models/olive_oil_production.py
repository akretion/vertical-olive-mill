# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import odoo.addons.decimal_precision as dp


class OliveOilProduction(models.Model):
    _name = 'olive.oil.production'
    _description = 'Olive Oil Production'
    _order = 'name desc'
    _inherit = ['mail.thread']

    name = fields.Char(string='Production Number', required=True, default='/')
    company_id = fields.Many2one(
        'res.company', string='Company',
        ondelete='cascade', required=True,
        states={'done': [('readonly', True)]},
        default=lambda self: self.env['res.company']._company_default_get(
            'olive.arrival'))
    season_id = fields.Many2one(
        'olive.season', string='Season', required=True,
        default=lambda self: self.env['olive.season'].get_current_season(),
        states={'done': [('readonly', True)]})
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse', required=True,
        default=lambda self: self._default_warehouse(),
        track_visibility='onchange')
    src_location_id = fields.Many2one(
        'stock.location', string='Palox', required=True,
        states={'done': [('readonly', True)]},
        domain=[('olive_type', '=', 'palox')],
        track_visibility='onchange')
    dest_location_id = fields.Many2one(
        'stock.location', string='Output Tank', required=True,
        states={'done': [('readonly', True)]},
        domain=[('olive_type', '=', 'tank')],
        track_visibility='onchange')
    olive_qty_compute = fields.Float(
        compute='_compute_olive_qty', readonly=True,
        string='Olive Quantity',
        digits=dp.get_precision('Olive Weight'),
        help="Total olive quantity in kg")
    olive_qty_done = fields.Float(
        string='Olive Quantity', readonly=True,
        digits=dp.get_precision('Olive Weight'),
        help="Total olive quantity in kg")
    olive_compensation_qty = fields.Float(
        string='Olive Compensation',
        digits=dp.get_precision('Olive Weight'),
        states={'done': [('readonly', True)]},
        track_visibility='onchange', help="Olive compensation in kg")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
        ], string='State', default='draft', readonly=True,
        track_visibility='onchange')
    done_datetime = fields.Datetime(string='Date Done', readonly=True)
    picking_id = fields.Many2one(
        'stock.picking', string='Picking', readonly=True, copy=False)

    _sql_constraints = [(
        'olive_compensation_qty_positive',
        'CHECK(olive_compensation_qty >= 0)',
        'The compensation quantity must be positive or 0.'),
        ]

    @api.depends('src_location_id')
    def _compute_olive_qty(self):
        for production in self:
            qty = production.src_location_id.get_total_qty_kg()
            production.olive_qty_compute = qty

    @api.model
    def _default_warehouse(self):
        company = self.env.user.company_id
        wh = company.olive_default_warehouse_id
        if not wh:
            wh = self.env['stock.warehouse'].search(
                [('company_id', '=', company.id)], limit=1)
        return wh

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'olive.oil.production')
        return super(OliveOilProduction, self).create(vals)

    def cancel(self):
        for production in self:
            if production.state == 'done':
                raise UserError(_(
                    "Cannot cancel production %s which is in 'done' state.")
                    % production.name)
            #if arrival.picking_id:
            #    raise UserError(_(
            #        "Cannot cancel arrival %s which is linked to picking %s.")
            #        % (arrival.name, arrival.picking_id.name))
        self.write({'state': 'cancel'})

    def validate(self):
        self.ensure_one()
        assert self.state == 'draft'
        prec = self.env['decimal.precision'].precision_get('Olive Weight')
        self.write({
            'state': 'done',
            'done_datetime': fields.Datetime.now(),
            'olive_qty_done': self.olive_qty_compute,
            #'picking_id': pick.id,
            })

    def unlink(self):
        for production in self:
            if production.state == 'done':
                raise UserError(_(
                    "Cannot delete production %s which is in Done state.")
                    % production.name)
            #if arrival.picking_id:
            #    raise UserError(_(
            #        "Cannot delete arrival %s which is linked to picking %s.")
            #        % (arrival.name, arrival.picking_id.name))
        return super(OliveOilProduction, self).unlink()
