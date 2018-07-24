# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class OliveArrival(models.Model):
    _name = 'olive.arrival'
    _description = 'Olive Arrival'
    _order = 'name desc'
    _inherit = ['mail.thread']

    name = fields.Char(string='Arrival Number', required=True, default='/')
    company_id = fields.Many2one(
        'res.company', string='Company',
        ondelete='cascade', required=True,
        states={'done': [('readonly', True)]},
        default=lambda self: self.env['res.company']._company_default_get(
            'olive.arrival'))
    partner_id = fields.Many2one(
        'res.partner', string='Olive Farmer', required=True, copy=False,
        domain=[('parent_id', '=', False), ('olive_farmer', '=', True)],
        states={'done': [('readonly', True)]},
        track_visibility='onchange')
    default_product_id = fields.Many2one(
        'product.product', string='Default Olive Type',
        states={'done': [('readonly', True)]},
        domain=[('olive_type', '=', 'olive')], track_visibility='onchange')
    default_src_location_id = fields.Many2one(
        'stock.location', string='Default Ochard',
        states={'done': [('readonly', True)]},
        domain=[('olive_type', '=', 'ochard')])
    leaf_removal = fields.Boolean(
        string='Leaf Removal', track_visibility='onchange',
        states={'done': [('readonly', True)]})
    qty = fields.Integer(
        compute='_compute_qty', readonly=True, store=True,
        track_visibility='onchange', string='Quantity',
        help="Olive quantity in kg")
    default_oil_destination = fields.Selection([
        ('withdrawal', 'Withdrawal'),
        ('sale', 'Sale'),
        ('mix', 'Mix'),
        ], string='Oil Destination', states={'done': [('readonly', True)]})
    purchase_qty = fields.Integer(
        string='Purchase Quantity', states={'done': [('readonly', True)]})
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
        ], string='State', default='draft', readonly=True,
        track_visibility='onchange')
    done_datetime = fields.Datetime(string='Date Done', readonly=True)
    line_ids = fields.One2many(
        'olive.arrival.line', 'arrival_id', string='Arrival Lines',
        states={'done': [('readonly', True)]})
    returned_case = fields.Integer(string='Returned Cases')
    returned_organic_case = fields.Integer(string='Returned Organic Cases')
    lended_case_id = fields.Many2one(
        'olive.lended.case', string='Lended Case Move', readonly=True)

    _sql_constraints = [(
        'qty_positive',
        'CHECK(qty >= 0)',
        'The quantity must be positive or 0.'), (
        'purchase_qty_positive',
        'CHECK(purchase_qty >= 0)',
        'The purchase quantity must be positive or 0.'), (
        'returned_case_positive',
        'CHECK(returned_case >= 0)',
        'The returned cases must be positive or 0.'),
        ]

    @api.depends('line_ids.qty')
    def _compute_qty(self):
        for arrival in self:
            qty = 0
            for line in arrival.line_ids:
                qty += line.qty
            arrival.qty = qty

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'olive.arrival')
        return super(OliveArrival, self).create(vals)

    def cancel(self):
        for arrival in self:
            if arrival.state == 'done':
                raise UserError(_(
                    "Cannot cancel arrival %s which is in 'done' state.")
                    % arrival.name)
        self.write({'state': 'cancel'})

    def validate(self):
        self.ensure_one()
        print "validate=", self
        assert self.state == 'draft'
        if not self.oil_destination:
            raise UserError(_(
                "The oil destination of arrival '%s' must be decided "
                "before validation.") % self.name)
        lended_case_id = False
        if self.returned_case or self.returned_organic_case:
            if self.returned_case > self.partner_id.olive_lended_case:
                raise UserError(_(
                    "The olive farmer '%s' currently has %d lended case(s) and "
                    "the olive arrival %s declares %d returned case(s).")
                    % (self.partner_id.display_name,
                       self.partner_id.olive_lended_case,
                       self.name,
                       self.returned_case))
            if self.returned_organic_case > self.partner_id.olive_lended_organic_case:
                raise UserError(_(
                    "The olive farmer '%s' currently has %d lended organic case(s) and "
                    "the olive arrival %s declares %d returned organic case(s).")
                    % (self.partner_id.display_name,
                       self.partner_id.olive_lended_organic_case,
                       self.name,
                       self.returned_organic_case))
            if self.lended_case_id:
                raise UserError(_(
                    "The arrival %s is already linked to a lended case move")
                    % self.name)
            lended_case = self.env['olive.lended.case'].create({
                'partner_id': self.partner_id.id,
                'qty': self.returned_case * -1,
                'organic_qty': self.returned_organic_case * -1,
                'notes': self.name,
                'company_id': self.company_id.id,
                })
            lended_case_id = lended_case.id
        returned_palox = self.env['stock.location']
        for line in self.line_ids:
            if not line.qty:
                raise UserError(_(
                    "On arrival %s, there is a line with null quantity")
                    % self.name)
            if line.dest_location_id.olive_borrower_partner_id:
                returned_palox |= line.dest_location_id
        # Mark palox as returned
        returned_palox.write({
            'olive_borrower_partner_id': False,
            'olive_borrowed_date': False,
            })
        self.write({
            'state': 'done',
            'done_datetime': fields.Datetime.now(),
            'lended_case_id': lended_case_id,
            })

    def unlink(self):
        for arrival in self:
            if arrival.state == 'done':
                raise UserError(_(
                    "Cannot delete arrival %s which is in Done state.")
                    % arrival.name)
        return super(OliveArrival, self).unlink()


class OliveArrivalLine(models.Model):
    _name = 'olive.arrival.line'
    _description = 'Olive Arrival Line'

    arrival_id = fields.Many2one(
        'olive.arrival', string='Arrival', ondelete='cascade')
    partner_id = fields.Many2one(
        related='arrival_id.partner_id', string='Olive Farmer', readonly=True)
    product_id = fields.Many2one(
        'product.product', string='Olive Type', required=True,
        domain=[('olive_type', '=', 'olive')])
    qty = fields.Integer(
        string='Olive Qty', help="Olive Quantity in Kg", required=True)
    src_location_id = fields.Many2one(
        'stock.location', string='Ochard', required=True,
        domain=[('olive_type', '=', 'ochard')])
    dest_location_id = fields.Many2one(
        'stock.location', string='Palox', required=True,
        domain=[('olive_type', '=', 'palox')])
    oil_destination = fields.Selection([
        ('withdrawal', 'Withdrawal'),
        ('sale', 'Sale'),
        ('mix', 'Mix'),
        ], string='Oil Destination')
    sale_qty = fields.Integer(string='Sale Quantity')

    _sql_constraints = [(
        'qty_positive',
        'CHECK(qty >= 0)',
        'The quantity must be positive or 0.')]
