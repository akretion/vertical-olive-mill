# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import odoo.addons.decimal_precision as dp
from odoo.tools import float_compare, float_is_zero, float_round

MIN_RATIO = 5
MAX_RATIO = 35


class OliveOilProduction(models.Model):
    _name = 'olive.oil.production'
    _description = 'Olive Oil Production'
    _order = 'planned_date desc, sequence'  # TODO Time and scheduling
    _inherit = ['mail.thread']

    name = fields.Char(string='Production Number', required=True, default='/')
    company_id = fields.Many2one(
        'res.company', string='Company', ondelete='cascade', required=True,
        states={'done': [('readonly', True)]},
        default=lambda self: self.env['res.company']._company_default_get(
            'olive.arrival'))
    season_id = fields.Many2one(
        'olive.season', string='Season', required=True,
        default=lambda self: self.env['olive.season'].get_current_season(),
        states={'done': [('readonly', True)]})
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse', required=True,
        default=lambda self: self.env.user._default_olive_mill_wh(),
        track_visibility='onchange')
    palox_id = fields.Many2one(
        'olive.palox', string='Palox', required=True, readonly=True,
        states={'draft': [('readonly', False)]}, track_visibility='onchange')
    sale_location_id = fields.Many2one(
        'stock.location', string='Sale Tank',
        states={'done': [('readonly', True)]},
        domain=[('olive_tank', '=', True)],
        track_visibility='onchange')
    # not a pb to have withdrawal_location_id required because
    # this field has a default value
    withdrawal_location_id = fields.Many2one(
        'stock.location', string='Withdrawal Location', required=True,
        states={'done': [('readonly', True)]},
        domain=[('olive_tank', '=', False)])
    shrinkage_location_id = fields.Many2one(
        'stock.location', string='Shrinkage Tank',
        states={'done': [('readonly', True)]},
        domain=[('olive_tank', '=', True)],
        track_visibility='onchange')
    olive_qty_compute = fields.Float(
        compute='_compute_lines', readonly=True, store=True,
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
        readonly=True, states={'ratio': [('readonly', False)]},
        track_visibility='onchange', help="Olive compensation in kg")
    olive_qty_total = fields.Float(
        string='Olive Compensation', compute='_compute_lines',
        digits=dp.get_precision('Olive Weight'), readonly=True, store=True)
    oil_destination = fields.Selection([
        ('withdrawal', 'Withdrawal'),
        ('sale', 'Sale'),
        ('mix', 'Mix'),
        ], string='Oil Destination', readonly=True)
    oil_product_id = fields.Many2one(
        'product.product', string='Oil Type', readonly=True)
    oil_qty_kg = fields.Float(
        string='Oil Qty', digits=dp.get_precision('Olive Weight'),
        readonly=True)  # written ratio2force wizard
    oil_qty = fields.Float(
        string='Oil Qty', digits=dp.get_precision('Olive Oil Volume'),
        compute='_compute_oil_qty', store=True, readonly=True)
    compensation_ratio = fields.Float(
        string='Compensation Ratio', digits=dp.get_precision('Olive Oil Ratio'),
        readonly=True, states={'ratio': [('readonly', False)]})
    ratio = fields.Float(
        string='Ratio', compute='_compute_ratio',
        digits=dp.get_precision('Olive Oil Ratio'), readonly=True, store=True,
        help="This ratio gives the number of liters of olive oil for "
        "100 Kg of olives.")  # Yes, it's a ratio between liters and kg !!!
    planned_date = fields.Date(
        string='Planned Date', default=fields.Date.context_today,
        states={'done': [('readonly', True)]}, track_visibility='onchange')
    sequence = fields.Integer()
    state = fields.Selection([
        ('draft', 'Palox Selection'),
        ('ratio', 'Enter Production Result'),
        ('force', 'Force Ratio'),
        ('pack', 'Package'),
        ('check', 'Final Check'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
        ], string='State', default='draft', readonly=True,
        track_visibility='onchange')
    done_datetime = fields.Datetime(
        string='Date Done', readonly=True, copy=False)
#    sale_picking_id = fields.Many2one(
#        'stock.picking', string='Sale Picking', readonly=True, copy=False)
    shrinkage_move_id = fields.Many2one(
        'stock.move', string='Shrinkage Stock Move', readonly=True, copy=False)
    line_ids = fields.One2many(
        'olive.arrival.line', 'production_id', string='Arrival Lines',
        states={'done': [('readonly', True)]})

    _sql_constraints = [(
        'olive_compensation_qty_positive',
        'CHECK(olive_compensation_qty >= 0)',
        'The compensation quantity must be positive or 0.'),
        ]

    @api.onchange('warehouse_id')
    def warehouse_change(self):
        if self.warehouse_id:
            if self.warehouse_id.olive_shrinkage_loc_id:
                self.shrinkage_location_id = self.warehouse_id.olive_shrinkage_loc_id
            if self.warehouse_id.olive_withdrawal_loc_id:
                self.withdrawal_location_id = self.warehouse_id.olive_withdrawal_loc_id

    @api.depends('line_ids.olive_qty', 'olive_compensation_qty')
    def _compute_lines(self):
        for production in self:
            qty = 0.0
            for line in production.line_ids:
                qty += line.olive_qty
            production.olive_qty_compute = qty
            production.olive_qty_total = qty + production.olive_compensation_qty

    @api.depends('oil_qty', 'olive_qty_total')
    def _compute_ratio(self):
        for production in self:
            ratio = 0.0
            if production.olive_qty_total:
                ratio = 100 * production.oil_qty / production.olive_qty_total
            production.ratio = ratio

    @api.depends('oil_qty_kg')
    def _compute_oil_qty(self):
        for production in self:
            if production.company_id.olive_oil_density:
                production.oil_qty = production.oil_qty_kg / production.company_id.olive_oil_density


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
            production.line_ids.write({'production_id': False})
        self.write({
            'state': 'cancel',
            'oil_qty_kg': 0,
            'olive_qty_compensation': 0,
            })

    def back2draft(self):
        self.ensure_one()
        assert self.state == 'cancel'
        if self.line_ids:
            raise UserError(_(
                "The cancelled production %s should not have any lines") % self.name)
        self.write({'state': 'draft'})

    def draft2ratio(self):
        """Attach arrival lines to olive.oil.production"""
        self.ensure_one()
        assert self.state == 'draft'
        if self.line_ids:
            raise UserError(_(
                "There shouldn't be any lines in production %s") % self.name)
        lines = self.env['olive.arrival.line'].search([
            ('palox_id', '=', self.palox_id.id),
            ('arrival_state', '=', 'done'),
            ('production_id', '=', False)])
        if not lines:
            raise UserError(_(
                "The palox %s is empty.") % self.palox_id.display_name)
        oil_dests = []
        oil_product_id = False
        prec = self.env['decimal.precision'].precision_get(
            'Olive Weight')
        for l in lines:
            oil_dests.append(l.oil_destination)
            if oil_product_id:
                if oil_product_id != l.oil_product_id.id:
                    raise UserError(_(
                        "The oil type is not the same "
                        "on all the lines of palox %s.") % self.palox_id.display_name)
                    # TODO improve error
            else:
                oil_product_id = l.oil_product_id.id
            if float_compare(l.olive_qty, 0, precision_digits=prec) <= 0:
                raise UserError(_(
                    "On line %s, the olive qty is null !") % l.name)
        if all([oil_dest == 'sale' for oil_dest in oil_dests]):
            oil_destination = 'sale'
        elif all([oil_dest == 'withdrawal' for oil_dest in oil_dests]):
            oil_destination = 'withdrawal'
        else:
            oil_destination = 'mix'

        lines.write({'production_id': self.id})

        compensation_ratio = self.company_id.olive_oil_average_ratio
        if compensation_ratio < MIN_RATIO or compensation_ratio > MAX_RATIO:
            raise UserError(_(
                "The compensation ratio (%s) is not realistic")
                % compensation_ratio)
        self.write({
            'state': 'ratio',
            'oil_product_id': oil_product_id,
            'oil_destination': oil_destination,
            'compensation_ratio': self.company_id.olive_oil_average_ratio,
            })

    def ratio2force(self):
        self.ensure_one()
        assert self.state == 'ratio'
        new_state = 'force'
        if len(self.line_ids) == 1:  # Skip force ratio step
            new_state = 'pack'
        self.write({
            'state': new_state,
            })
        self.set_qty_on_lines()

    def force2pack(self):
        self.ensure_one()
        assert self.state == 'force'
        self.write({
            'state': 'pack',
            })

    def pack2check(self):
        self.ensure_one()
        assert self.state == 'pack'
        self.write({
            'state': 'check',
            })

    def oil_qty_compute_other_vals(self, oil_qty, ratio):
        oil_prec = self.env['decimal.precision'].precision_get('Olive Oil Volume')
        olive_prec = self.env['decimal.precision'].precision_get('Olive Weight')
        density = self.company_id.olive_oil_density
        shrinkage_ratio = self.company_id.olive_production_shrinkage_ratio
        if not density:
            raise UserError(_(
                "Missing Olive Oil Density on company '%s'")
                % self.company_id.display_name)
        # oil_qty = float_round(oil_qty, precision_digits=oil_prec)
        oil_qty_kg = float_round(
            oil_qty * density, precision_digits=olive_prec)
        shrinkage_tank_oil_qty = float_round(
            oil_qty * shrinkage_ratio / 100, precision_digits=oil_prec)
        shrinkage_tank_oil_qty_kg = float_round(
            shrinkage_tank_oil_qty * density, precision_digits=olive_prec)
        withdrawal_oil_qty = float_round(
            oil_qty - shrinkage_tank_oil_qty, precision_digits=oil_prec)
        withdrawal_oil_qty_kg = float_round(
            oil_qty_kg - shrinkage_tank_oil_qty_kg, precision_digits=olive_prec)
        vals = {
            'oil_qty_kg': oil_qty_kg,
            'oil_qty': oil_qty,
            'oil_ratio': ratio,
            'shrinkage_tank_oil_qty': shrinkage_tank_oil_qty,
            'shrinkage_tank_oil_qty_kg': shrinkage_tank_oil_qty_kg,
            'withdrawal_oil_qty_kg': withdrawal_oil_qty_kg,
            'withdrawal_oil_qty': withdrawal_oil_qty,
            }
        return vals

    def set_qty_on_lines(self, force_ratio=False):
        """force_ratio=(line_to_force, ratio)"""
        self.ensure_one()
        oil_prec = self.env['decimal.precision'].precision_get('Olive Oil Volume')
        ratio_prec = self.env['decimal.precision'].precision_get('Olive Oil Ratio')
        last_line_oil_qty = self.oil_qty
        if force_ratio:
            first_line_to_process = force_ratio[0]
            first_line_ratio = force_ratio[1]
        else:
            first_line_to_process = self.line_ids[0]
            first_line_ratio = self.ratio
        first_line_ratio = float_round(
            first_line_ratio, precision_digits=ratio_prec)
        first_line_oil_qty = float_round(
            first_line_to_process.olive_qty * first_line_ratio / 100,
            precision_digits=oil_prec)
        first_line_vals = self.oil_qty_compute_other_vals(
            first_line_oil_qty, first_line_ratio)
        first_line_to_process.write(first_line_vals)
        last_line_oil_qty -= first_line_oil_qty
        total_olive_qty_without_first_line = self.olive_qty_compute - first_line_to_process.olive_qty
        total_oil_qty_without_first_line = self.oil_qty - first_line_oil_qty
        lines = [line for line in self.line_ids if line != first_line_to_process]
        while lines:
            line = lines.pop()
            if lines:
                # compute oil qty at the pro-rata of olive qty
                oil_qty = float_round(
                    line.olive_qty * total_oil_qty_without_first_line / total_olive_qty_without_first_line, precision_digits=oil_prec)
                ratio = float_round(
                    100 * oil_qty / line.olive_qty, precision_digits=ratio_prec)
                last_line_oil_qty -= oil_qty
            else:
                # last line, use a substraction
                oil_qty = last_line_oil_qty
                ratio = float_round(
                    100 * oil_qty / line.olive_qty, precision_digits=ratio_prec)
            vals = self.oil_qty_compute_other_vals(oil_qty, ratio)
            line.write(vals)


    def check2done(self):
        self.ensure_one()
        assert self.state == 'check'
        splo = self.env['stock.production.lot']
        smo = self.env['stock.move']
        prec = self.env['decimal.precision'].precision_get('Olive Weight')
        withdrawal_location_id = self.warehouse_id.olive_withdrawal_loc_id.id
        stock_loc_id = self.warehouse_id.lot_stock_id.id
        oil_product = self.oil_product_id
        total_shrinkage_oil_qty = 0.0
        for line in self.line_ids:
            # TODO add if withdrawal !!!!
            # create prod lot
            prodlot = splo.create({
                'arrival_line_id': line.id,
                'product_id': oil_product.id,
                'name': line.name,
                })
            # create move from virtual prod > Withdrawal loc
            move = smo.create({
                'product_id': oil_product.id,
                'name': _('Olive Oil Production %s: Withdrawal related to arrival line %s') % (self.name, line.name),
                'location_id': oil_product.property_stock_production.id,
                'location_dest_id': withdrawal_location_id,
                'product_uom': oil_product.uom_id.id,
                'origin': self.name,
                'product_uom_qty': line.withdrawal_oil_qty,
                'restrict_lot_id': prodlot.id,
                'restrict_partner_id': line.partner_id.id,
                })
            move.action_done()
            for extra in line.extra_ids:
                if extra.product_id.tracking and extra.product_id.tracking != 'none':
                    raise UserError(_(
                        "Can't select the product '%s' in extra items of "
                        "line %s because it is tracked by lot or serial.")
                        % (extra.product_id.display_name, line.name))
                extra_move = smo.create({
                    'product_id': extra.product_id.id,
                    'name': _('Olive Oil Production %s: Extra Item Withdrawal related to arrival line %s') % (self.name, line.name),
                    'location_id': stock_loc_id,
                    'location_dest_id': withdrawal_location_id,
                    'product_uom': extra.product_id.uom_id.id,
                    'origin': self.name,
                    'product_uom_qty': extra.qty,
                    'restrict_partner_id': line.partner_id.id,
                    })
                extra_move.action_done()
                assert extra_move.state == 'done'
            assert move.state == 'done'
            total_shrinkage_oil_qty += line.shrinkage_tank_oil_qty
        if not oil_product.shrinkage_prodlot_id:
            raise UserError(_(
                "Missing shrinkage production lot on product '%s'.")
                % oil_product.display_name)
        shrinkage_move = smo.create({
            'product_id': oil_product.id,
            'name': _('Olive Oil Production %s: Shrinkage') % self.name,
            'location_id': oil_product.property_stock_production.id,
            'location_dest_id': self.warehouse_id.olive_shrinkage_loc_id.id,
            'product_uom': oil_product.uom_id.id,
            'origin': self.name,
            'product_uom_qty': total_shrinkage_oil_qty,
            'restrict_lot_id': oil_product.shrinkage_prodlot_id.id,
            })
        shrinkage_move.action_done()

        self.write({
            'state': 'done',
            'done_datetime': fields.Datetime.now(),
            'olive_qty_done': self.olive_qty_compute,
            'shrinkage_move_id': shrinkage_move.id,
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
