# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import odoo.addons.decimal_precision as dp


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
    season_id = fields.Many2one(
        'olive.season', string='Season', required=True,
        default=lambda self: self.env['olive.season'].get_current_season(),
        states={'done': [('readonly', True)]})
    partner_id = fields.Many2one(
        'res.partner', string='Olive Farmer', required=True,
        domain=[('parent_id', '=', False), ('olive_farmer', '=', True)],
        states={'done': [('readonly', True)]},
        track_visibility='onchange')
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse', required=True,
        default=lambda self: self._default_warehouse(),
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
    qty = fields.Float(
        compute='_compute_qty', readonly=True, store=True,
        track_visibility='onchange', string='Total Quantity',
        digits=dp.get_precision('Olive Weight'),
        help="Total olive quantity in kg")
    default_oil_destination = fields.Selection([
        ('withdrawal', 'Withdrawal'),
        ('sale', 'Sale'),
        ('mix', 'Mix'),
        ], string='Default Oil Destination',
        states={'done': [('readonly', True)]})
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
    picking_id = fields.Many2one(
        'stock.picking', string='Picking', readonly=True, copy=False)
    # TODO returned palox that are not re-used

    _sql_constraints = [(
        'qty_positive',
        'CHECK(qty >= 0)',
        'The quantity must be positive or 0.'), (
        'returned_case_positive',
        'CHECK(returned_case >= 0)',
        'The returned cases must be positive or 0.'),
        ]

    @api.depends('line_ids.qty')
    def _compute_qty(self):
        for arrival in self:
            qty = 0.0
            for line in arrival.line_ids:
                qty += line.qty
            arrival.qty = qty

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
                'olive.arrival')
        return super(OliveArrival, self).create(vals)

    def cancel(self):
        for arrival in self:
            if arrival.state == 'done':
                raise UserError(_(
                    "Cannot cancel arrival %s which is in 'done' state.")
                    % arrival.name)
            if arrival.picking_id:
                raise UserError(_(
                    "Cannot cancel arrival %s which is linked to picking %s.")
                    % (arrival.name, arrival.picking_id.name))
        self.write({'state': 'cancel'})

    def validate(self):
        self.ensure_one()
        assert self.state == 'draft'
        if not self.line_ids:
            raise UserError(_(
                "Missing lines on arrival '%s'.") % self.name)
        prec = self.env['decimal.precision'].precision_get('Olive Weight')
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
        pvals = {
            'partner_id': self.partner_id.id,
            'company_id': self.company_id.id,
            'picking_type_id': self.warehouse_id.in_type_id.id,
            'origin': self.name,
            'move_type': 'one',
            'location_id': self.line_ids[0].src_location_id.id,
            'location_dest_id': self.line_ids[0].dest_location_id.id,
            'move_lines': [],
            }
        partner_organic_cert = self.partner_id.olive_organic_certified
        for line in self.line_ids:
            if float_is_zero(line.qty, precision_digits=prec):
                raise UserError(_(
                    "On arrival %s, there is a line with null quantity")
                    % self.name)
            if line.dest_location_id.olive_borrower_partner_id:
                returned_palox |= line.dest_location_id
            if line.product_id.olive_culture_type in ('organic', 'conversion'):
                if not partner_organic_cert:
                    raise UserError(_(
                        "For the arrival %s, the olives '%s' are '%s' "
                        "but the farmer '%s' has no organic certification.") % (
                            self.name,
                            line.product_id.name,
                            line.product_id.olive_culture_type,
                            self.partner_id.display_name))
                elif not partner_organic_cert.startswith(
                        line.product_id.olive_culture_type):
                    raise UserError(_(
                        "For the arrival %s, the olives '%s' are '%s' "
                        "but the farmer '%s' has a certification status '%s'.") % (
                            self.name,
                            line.product_id.name,
                            line.product_id.olive_culture_type,
                            self.partner_id.display_name,
                            partner_organic_cert.split('-')[0],
                            ))
            pvals['move_lines'].append((0, 0, {
                'name': line.product_id.display_name,
                'product_id': line.product_id.id,
                'product_uom': line.product_id.uom_id.id,
                'company_id': self.company_id.id,
                'product_uom_qty': line.qty,
                'location_id': line.src_location_id.id,
                'location_dest_id': line.dest_location_id.id,
                'origin': self.name,
                }))
        # Mark palox as returned
        returned_palox.write({
            'olive_borrower_partner_id': False,
            'olive_borrowed_date': False,
            })
        # TODO : if palox already has some olives in, check that the new olives are "compatible"
        # also check that we don't overload a palox
        pick = self.env['stock.picking'].create(pvals)
        # mark as todo
        pick.action_confirm()
        if pick.state != 'assigned':
            raise UserError(_(
                "Houston, we have a problem! Picking state is %s "
                "(should be assigned). ") % pick.state)
        pick.action_pack_operation_auto_fill()
        pick.do_new_transfer()
        if pick.state != 'done':
            raise UserError(_(
                "Houston, we have a problem! Picking state is %s "
                "(should be available). ") % pick.state)
        self.write({
            'state': 'done',
            'done_datetime': fields.Datetime.now(),
            'lended_case_id': lended_case_id,
            'picking_id': pick.id,
            })

    def unlink(self):
        for arrival in self:
            if arrival.state == 'done':
                raise UserError(_(
                    "Cannot delete arrival %s which is in Done state.")
                    % arrival.name)
            if arrival.picking_id:
                raise UserError(_(
                    "Cannot delete arrival %s which is linked to picking %s.")
                    % (arrival.name, arrival.picking_id.name))
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
    product_olive_culture_type = fields.Selection(
        related='product_id.olive_culture_type', store=True, readonly=True)
    qty = fields.Float(
        string='Olive Qty', help="Olive Quantity in Kg", required=True,
        digits=dp.get_precision('Olive Weight'))
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
    sale_qty = fields.Float(
        string='Sale Quantity', digits=dp.get_precision('Olive Weight'))
    ripeness = fields.Selection([  # maturité
        ('green', 'Green'),
        ('in_between', 'In Between'),  # Tournantes
        ('optimal', 'Optimal'),
        ('overripen', 'Over Ripen'),  # surmatures
        ], string='Ripeness', required=True)
    sanitary_state = fields.Selection([
        ('good', 'Good'),
        ('average', 'Average'),
        ('fair', 'Fair'),  # Passable
        ], string='Sanitary State', required=True)
    oil_product_id = fields.Many2one(
        'product.product', string='Oil Type', required=True,
        domain=[('olive_type', '=', 'oil')])

    _sql_constraints = [(
        'qty_positive',
        'CHECK(qty >= 0)',
        'The quantity must be positive or 0.'), (
        'sale_qty_positive',
        'CHECK(sale_qty >= 0)',
        'The sale quantity must be positive or 0.'),
        ]

    @api.constrains('product_id', 'oil_product_id', 'oil_destination', 'sale_qty')
    def check_arrival_line(self):
        prec = self.env['decimal.precision'].precision_get('Olive Weight')
        for line in self:
            if line.product_id.olive_culture_type != line.oil_product_id.olive_culture_type:
                raise ValidationError(_(
                    "On one of the lines of arrival %s, the olives '%s' have "
                    "a culture type '%s', but the selected oil '%s' have "
                    "a culture type '%s'.")
                    % (line.arrival_id.name, line.product_id.name,
                       line.product_id.olive_culture_type,
                       line.oil_product_id.name,
                       line.oil_product_id.olive_culture_type))
            if (
                    line.oil_destination in ('sale', 'mix') and
                    float_is_zero(line.sale_qty, precision_digits=prec)):
                raise ValidationError(_(
                    "On one of the lines of arrival %s, the oil destination "
                    "is '%s', so you must enter a sale quantity.")
                    % (line.arrival_id.name, line.line.oil_destination))

    @api.onchange('oil_destination', 'sale_qty')
    def oil_destination_change(self):
        if self.oil_destination == 'withdrawal' and self.sale_qty:
            self.sale_qty = 0
