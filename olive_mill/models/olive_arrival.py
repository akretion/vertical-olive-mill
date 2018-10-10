# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero
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
    partner_olive_culture_type = fields.Selection(
        related='partner_id.olive_culture_type', readonly=True)
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse', required=True,
        default=lambda self: self.env.user._default_olive_mill_wh(),
        track_visibility='onchange')
    default_variant_id = fields.Many2one(
        'olive.variant', string='Default Olive Variant',
        states={'done': [('readonly', True)]})
    default_ochard_id = fields.Many2one(
        'olive.ochard', string='Default Ochard',
        states={'done': [('readonly', True)]})
    leaf_removal = fields.Boolean(
        string='Leaf Removal', track_visibility='onchange',
        states={'done': [('readonly', True)]})
    olive_qty = fields.Float(
        compute='_compute_olive_qty', readonly=True, store=True,
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
    date = fields.Date(
        string='Arrival Date', track_visibility='onchange',
        default=fields.Date.context_today,
        states={'done': [('readonly', True)]})
    done_datetime = fields.Datetime(string='Date Done', readonly=True)
    line_ids = fields.One2many(
        'olive.arrival.line', 'arrival_id', string='Arrival Lines',
        states={'done': [('readonly', True)]})
    returned_case = fields.Integer(string='Returned Cases')
    returned_organic_case = fields.Integer(string='Returned Organic Cases')
    lended_case_id = fields.Many2one(
        'olive.lended.case', string='Lended Case Move', readonly=True)
    returned_palox_ids = fields.Many2many(
        'olive.palox', string='Other Returned Palox',
        help="Select returned palox other than those used in the arrival lines")

    _sql_constraints = [(
        'qty_positive',
        'CHECK(qty >= 0)',
        'The quantity must be positive or 0.'), (
        'returned_case_positive',
        'CHECK(returned_case >= 0)',
        'The returned cases must be positive or 0.'),
        ]

    @api.depends('line_ids.olive_qty')
    def _compute_olive_qty(self):
        for arrival in self:
            qty = 0.0
            for line in arrival.line_ids:
                qty += line.olive_qty
            arrival.olive_qty = qty

    @api.onchange('partner_id')
    def partner_id_change(self):
        if self.partner_id:
            ochards = self.env['olive.ochard'].search([
                ('partner_id', '=', self.partner_id.id)])
            if len(ochards) == 1:
                self.default_ochard_id = ochards
        else:
            self.default_ochard_id = False

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
        returned_palox = self.env['olive.palox']
        partner_olive_culture_type = self.partner_id.olive_culture_type
        oil_prec = self.env['decimal.precision'].precision_get('Oil Volume')
        for line in self.line_ids:
            if float_is_zero(line.olive_qty, precision_digits=prec):
                raise UserError(_(
                    "On line %s, the olive quantity is null")
                    % line.name)
            if line.palox_id.borrower_partner_id:
                returned_palox |= line.palox_id
            for palox in self.returned_palox_ids:
                returned_palox |= palox
            if line.oil_product_id.olive_culture_type != partner_olive_culture_type:
                raise UserError(_(
                    "On line %s, the destination oil '%s' is '%s' "
                    "but the farmer '%s' is '%s'.") % (
                        line.name,
                        line.oil_product_id.name,
                        line.oil_product_id.olive_culture_type,
                        self.partner_id.display_name,
                        partner_olive_culture_type,
                        ))
            if (
                    line.oil_destination == 'mix' and
                    float_is_zero(line.mix_withdrawal_oil_qty, precision_digits=prec)):
                raise UserError(_(
                    "On line %s, the oil destination is 'mix' so you must enter "
                    "the requested withdrawal qty") % line.name)

        # Mark palox as returned
        returned_palox.write({
            'borrower_partner_id': False,
            'borrowed_date': False,
            })
        # TODO : if palox already has some olives in, check that the new olives are "compatible"
        # also check that we don't overload a palox
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

    name = fields.Char(
        string='Arrival Line Number', required=True, readonly=True, default='/')
    arrival_id = fields.Many2one(
        'olive.arrival', string='Arrival', ondelete='cascade')
    company_id = fields.Many2one(
        related='arrival_id.company_id', string='Company', store=True, readonly=True)
    arrival_state = fields.Selection(
        related='arrival_id.state', string='Arrival State', readonly=True, store=True)
    arrival_date = fields.Date(
        related='arrival_id.date', readonly=True, store=True)
    partner_id = fields.Many2one(
        related='arrival_id.partner_id', string='Olive Farmer', readonly=True,
        store=True)
    partner_olive_culture_type = fields.Selection(
        related='arrival_id.partner_id.olive_culture_type', readonly=True)
    variant_id = fields.Many2one(
        'olive.variant', string='Olive Variant', required=True)
    olive_qty = fields.Float(
        string='Olive Qty', help="Olive Quantity in Kg", required=True,
        digits=dp.get_precision('Olive Weight'))
    ochard_id = fields.Many2one(
        'olive.ochard', string='Ochard', required=True)
    palox_id = fields.Many2one(
        'olive.palox', string='Palox', required=True)
    oil_destination = fields.Selection([
        ('withdrawal', 'Withdrawal'),
        ('sale', 'Sale'),
        ('mix', 'Mix'),
        ], string='Oil Destination')
    mix_withdrawal_oil_qty = fields.Float(
        string='Requested Withdrawal Qty (L)',
        digits=dp.get_precision('Olive Oil Volume'),
        help="Quantity of olive oil withdrawn by the farmer in liters")
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
    production_id = fields.Many2one(
        'olive.oil.production', string='Production', ondelete='restrict')
    production_state = fields.Selection(
        related='production_id.state', string='Production State',
        readonly=True, store=True)
    oil_ratio = fields.Float(
        string='Oil Ratio', digits=dp.get_precision('Olive Oil Ratio'))
    extra_ids = fields.One2many(
        'olive.arrival.line.extra', 'line_id', string="Extra Items")

    # START fields BEFORE shrinkage BEFORE filter_loss
    oil_qty_kg = fields.Float(  # Includes compensation
        readonly=True, digits=dp.get_precision('Olive Oil Volume'))
    oil_qty = fields.Float(  # Includes compensation
        readonly=True, digits=dp.get_precision('Olive Oil Volume'))
    compensation_oil_qty_kg = fields.Float(
        readonly=True, digits=dp.get_precision('Olive Oil Volume'))
    compensation_oil_qty = fields.Float(
        readonly=True, digits=dp.get_precision('Olive Oil Volume'))
    nocompensation_oil_qty_kg = fields.Float(
        readonly=True, digits=dp.get_precision('Olive Oil Volume'))
    nocompensation_oil_qty = fields.Float(
        readonly=True, digits=dp.get_precision('Olive Oil Volume'))
    # END fields BEFORE shrinkage BEFORE filter_loss


    shrinkage_tank_oil_qty_kg = fields.Float(
        readonly=True, digits=dp.get_precision('Olive Weight'))
    shrinkage_tank_oil_qty = fields.Float(
        readonly=True, digits=dp.get_precision('Olive Oil Volume'))

    # START fields AFTER shrinkage
    withdrawal_oil_qty_kg = fields.Float(
        readonly=True, digits=dp.get_precision('Olive Weight'))
    withdrawal_oil_qty = fields.Float(
        readonly=True, digits=dp.get_precision('Olive Oil Volume'))
    withdrawal_compensation_oil_qty_kg = fields.Float(
        readonly=True, digits=dp.get_precision('Olive Weight'))
    withdrawal_compensation_oil_qty = fields.Float(
        readonly=True, digits=dp.get_precision('Olive Oil Volume'))
    withdrawal_nocompensation_oil_qty_kg = fields.Float(
        readonly=True, digits=dp.get_precision('Olive Weight'))
    withdrawal_nocompensation_oil_qty = fields.Float(
        readonly=True, digits=dp.get_precision('Olive Oil Volume'))
    withdrawal_move_id = fields.Many2one(
        'stock.move', string='Withdrawal Stock Move', readonly=True)
    # END fields AFTER shrinkage

    to_sale_tank_oil_qty = fields.Float(
        readonly=True, digits=dp.get_precision('Olive Oil Volume'))
    filter_loss_oil_qty = fields.Float(
        readonly=True, digits=dp.get_precision('Olive Oil Volume'))
    sale_without_shrinkage_oil_qty = fields.Float(
        readonly=True, digits=dp.get_precision('Olive Oil Volume'))

    # ATTENTION : freinte : UNIQUEMENT quand c'est un total retrait

    _sql_constraints = [(
        'olive_qty_positive',
        'CHECK(olive_qty >= 0)',
        'The olive quantity must be positive or 0.'), (
        'mix_withdrawal_oil_qty_qty_positive',
        'CHECK(mix_withdrawal_oil_qty >= 0)',
        'The requested withdrawal qty must be positive or 0.'),
        ]

    def validate_oil_qty(self):
        for line in self:
            oil_qty_kg = line.oil_ratio * line.olive_qty
            sale_qty_kg = withdrawal_oil_qty_kg = 0.0
            if line.oil_destination == 'sale':
                sale_qty_kg = oil_qty_kg
            elif line.oil_destination == 'withdrawal':
                withdrawal_oil_qty_kg = oil_qty_kg
            elif line.oil_destination == 'mix':
                print "xx"
            line.oil_qty_kg = oil_qty_kg
            line.oil_qty = line.company_id.olive_oil_kg2liter(oil_qty_kg)


#    @api.constrains('oil_destination', 'sale_oil_qty')
#    def check_arrival_line(self):
#        prec = self.env['decimal.precision'].precision_get('Olive Weight')
#        for line in self:
#            if (
#                    line.oil_destination in ('sale', 'mix') and
#                    float_is_zero(line.sale_qty, precision_digits=prec)):
#                raise ValidationError(_(
#                    "On one of the lines of arrival %s, the oil destination "
#                    "is '%s', so you must enter a sale quantity.")
#                    % (line.arrival_id.name, line.line.oil_destination))

    @api.onchange('oil_destination')
    def oil_destination_change(self):
        if self.oil_destination != 'mix':
            # self.mix_sale_oil_qty = 0
            self.mix_withdrawal_oil_qty = 0

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'olive.arrival.line')
        return super(OliveArrivalLine, self).create(vals)

    @api.depends('name', 'partner_id')
    def name_get(self):
        res = []
        for rec in self:
            name = rec.name
            if rec.partner_id:
                name = u'%s (%s)' % (name, rec.partner_id.name)
            res.append((rec.id, name))
        return res


class OliveArrivalLineExtra(models.Model):
    _name = 'olive.arrival.line.extra'
    _description = 'Extra items linked to the arrival line'

    line_id = fields.Many2one(
        'olive.arrival.line', string='Arrival Line', ondelete='cascade')
    product_id = fields.Many2one(
        'product.product', string='Extra Product',
        required=True, ondelete='restrict')
    qty = fields.Float(
        string='Quantity',
        digits=dp.get_precision('Product Unit of Measure'), required=True)
    uom_id = fields.Many2one(
        related='product_id.uom_id', readonly=True)
