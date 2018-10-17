# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import odoo.addons.decimal_precision as dp
from odoo.tools import float_compare, float_is_zero, float_round
from dateutil.relativedelta import relativedelta


MIN_RATIO = 5
MAX_RATIO = 35


class OliveOilProduction(models.Model):
    _name = 'olive.oil.production'
    _description = 'Olive Oil Production'
    _order = 'date desc, sequence'  # TODO Time and scheduling
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
        domain=[('olive_mill', '=', True)],
        default=lambda self: self.env.user._default_olive_mill_wh(),
        track_visibility='onchange')
    palox_id = fields.Many2one(
        'olive.palox', string='Palox', required=True, readonly=True,
        states={'draft': [('readonly', False)]}, track_visibility='onchange')
    # STOCK LOCATIONS
    sale_location_id = fields.Many2one(
        'stock.location', string='Sale Tank',
        states={'done': [('readonly', True)]},
        domain=[('olive_tank', '=', True), ('usage', '=', 'internal')],
        track_visibility='onchange')
    # not a pb to have withdrawal_location_id required because
    # this field has a default value
    withdrawal_location_id = fields.Many2one(
        'stock.location', string='Withdrawal Location', required=True,
        states={'done': [('readonly', True)]},
        domain=[('olive_tank', '=', False), ('usage', '=', 'internal')])
    shrinkage_location_id = fields.Many2one(
        'stock.location', string='Shrinkage Tank',
        states={'done': [('readonly', True)]},
        domain=[('olive_tank', '=', True)],
        track_visibility='onchange')
    compensation_location_id = fields.Many2one(
        'stock.location', string='Compensation Tank',
        readonly=True, states={'draft': [('readonly', False)]},
        domain=[('olive_tank', '=', True)], track_visibility='onchange')
    compensation_sale_location_id = fields.Many2one(
        'stock.location', string='Compensation Sale Tank',
        states={'done': [('readonly', True)]},
        domain=[('olive_tank', '=', True), ('usage', '=', 'internal')],
        track_visibility='onchange')
    compensation_type = fields.Selection([
        ('none', 'No Compensation'),
        ('first', 'First of the Day'),
        ('last', 'Last of the Day'),
        ], string='Compensation Type', default='none',
        readonly=True, states={'draft': [('readonly', False)], 'ratio': [('readonly', False)]})
    compensation_last_olive_qty = fields.Float(
        string='Olive Compensation Qty',
        digits=dp.get_precision('Olive Weight'),
        readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='onchange', help="Olive compensation in kg")
    compensation_ratio = fields.Float(
        string='Compensation Ratio', digits=dp.get_precision('Olive Oil Ratio'),
        readonly=True, states={'draft': [('readonly', False)]})
    olive_qty = fields.Float(
        string='Olive Qty', compute='_compute_lines',
        digits=dp.get_precision('Olive Weight'), readonly=True, store=True,
        help='Olive quantity without compensation in Kg')
    compensation_oil_qty = fields.Float(
        string='Oil Compensation Last of Day (L)',
        digits=dp.get_precision('Olive Oil Volume'), readonly=True)
    compensation_oil_qty_kg = fields.Float(
        string='Oil Compensation Last of Day (kg)',
        digits=dp.get_precision('Olive Weight'), readonly=True)
    oil_destination = fields.Selection([
        ('withdrawal', 'Withdrawal'),
        ('sale', 'Sale'),
        ('mix', 'Mix'),
        ], string='Oil Destination', compute='_compute_oil_destination', readonly=True)
    oil_product_id = fields.Many2one(
        'product.product', string='Oil Type', readonly=True)
    oil_qty_kg = fields.Float(
        string='Oil Quantity (kg)', digits=dp.get_precision('Olive Weight'),
        readonly=True)  # written by ratio2force wizard
    oil_qty = fields.Float(
        string='Oil Quantity (L)', digits=dp.get_precision('Olive Oil Volume'),
        readonly=True)  # written by ratio2force wizard
    ratio = fields.Float(
        string='Ratio', compute='_compute_ratio',
        digits=dp.get_precision('Olive Oil Ratio'), readonly=True, store=True,
        help="This ratio gives the number of liters of olive oil for "
        "100 Kg of olives.")  # Yes, it's a ratio between liters and kg !!!
    date = fields.Date(
        string='Date', default=fields.Date.context_today,
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
    shrinkage_move_id = fields.Many2one(
        'stock.move', string='Shrinkage Stock Move', readonly=True, copy=False)
    line_ids = fields.One2many(
        'olive.arrival.line', 'production_id', string='Arrival Lines',
        readonly=True)

    _sql_constraints = [
        ('oil_qty_kg_positive', 'CHECK(oil_qty_kg) >= 0', 'The oil quantity must be positive.'),
        ('compensation_last_olive_qty_positive', 'CHECK(compensation_last_olive_qty) >= 0', 'The compensation olive quantity must be positive.'),
        ('compensation_oil_qty_positive', 'CHECK(compensation_oil_qty) >= 0', 'The compensation oil quantity must be positive.'),
        ]

    @api.constrains('compensation_ratio', 'compensation_type')
    def check_production(self):
        for prod in self:
            if prod.compensation_type == 'last':
                cratio = prod.compensation_ratio
                if cratio < MIN_RATIO or cratio > MAX_RATIO:
                    raise ValidationError(_(
                        "The compensation ratio (%s %%) is not realistic.")
                        % cratio)

    @api.onchange('warehouse_id')
    def warehouse_change(self):
        if self.warehouse_id:
            wh = self.warehouse_id
            if wh.olive_shrinkage_loc_id:
                self.shrinkage_location_id = wh.olive_shrinkage_loc_id
            if wh.olive_withdrawal_loc_id:
                self.withdrawal_location_id = wh.olive_withdrawal_loc_id

    @api.onchange('palox_id')
    def palox_change(self):
        if self.palox_id:
            self.oil_product_id = self.palox_id.oil_product_id
        else:
            self.oil_product_id = False

    @api.onchange('compensation_type')
    def compensation_type_change(self):
        cqty_last = 0
        cratio = 0
        cloc = False
        res = {'warning': {}}
        wh = self.warehouse_id
        if self.compensation_type == 'last':
            cloc = wh.olive_compensation_loc_id
            cratio = wh.olive_oil_compensation_ratio
            cqty_last = wh.olive_compensation_last_qty
            today_dt = fields.Date.from_string(fields.Date.context_today(self))
            yesterday = fields.Date.to_string(today_dt - relativedelta(days=1))
            last_update = wh.olive_oil_compensation_ratio_update_date
            if last_update:
                if last_update < yesterday:
                    res['warning']['message'] = _(
                        "The last update of the compensation ratio for the "
                        "warehouse '%s' took place on %s. You should update "
                        "the compensation ratio on that warehouse.") % (
                            wh.display_name, last_update)
            else:
                res['warning']['message'] = _(
                    "The field 'Last update of the compensation ratio' is "
                    "empty on the warehouse '%s'.") % wh.display_name
        elif self.compensation_type == 'first':
            cloc = wh.olive_compensation_loc_id
        self.compensation_location_id = cloc
        self.compensation_last_olive_qty = cqty_last
        self.compensation_ratio = cratio
        return res

    @api.depends('line_ids.olive_qty')
    def _compute_lines(self):
        res = self.env['olive.arrival.line'].read_group(
            [('production_id', 'in', self.ids)],
            ['production_id', 'olive_qty'], ['production_id'])
        for re in res:
            production = self.browse(re['production_id'][0])
            production.olive_qty = re['olive_qty']

    @api.depends(
            'oil_qty', 'olive_qty', 'compensation_type',
            'compensation_last_olive_qty')
    def _compute_ratio(self):
        for prod in self:
            ratio = 0.0
            olive_qty = prod.olive_qty
            if prod.compensation_type == 'last':
                olive_qty += prod.compensation_last_olive_qty
            if olive_qty:
                ratio = 100 * prod.oil_qty / olive_qty
            prod.ratio = ratio

    @api.depends('line_ids.oil_destination')
    def _compute_oil_destination(self):
        for production in self:
            dests = [line.oil_destination for line in production.line_ids]
            if all([dest == 'sale' for dest in dests]):
                oil_destination = 'sale'
            elif all([dest == 'withdrawal' for dest in dests]):
                oil_destination = 'withdrawal'
            else:
                oil_destination = 'mix'
            production.oil_destination = oil_destination

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
            production.line_ids.write({'production_id': False})
            production.palox_id.oil_product_id = False
        self.write({
            'state': 'cancel',
            'oil_qty_kg': 0,
            'compensation_first_oil_qty': 0,
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
            ('warehouse_id', '=', self.warehouse_id.id),
            ('arrival_state', '=', 'done'),
            ('production_id', '=', False)])
        if not lines:
            raise UserError(_(
                "The palox %s is empty or currently in production.")
                % self.palox_id.display_name)
        oil_dests = []
        oil_product = False
        pr_oli = self.env['decimal.precision'].precision_get('Olive Weight')
        for l in lines:
            oil_dests.append(l.oil_destination)
            if oil_product:
                if oil_product != l.oil_product_id:
                    raise UserError(_(
                        "The oil type is not the same "
                        "on all the lines of palox %s.") % self.palox_id.display_name)
                    # TODO improve error
            else:
                oil_product = l.oil_product_id
            if float_compare(l.olive_qty, 0, precision_digits=pr_oli) <= 0:
                raise UserError(_(
                    "On line %s, the olive qty is null !") % l.name)
        lines.write({'production_id': self.id})

        compensation_ratio = compensation_first_oil_qty = False
        ctype = self.compensation_type
        self.compensation_check_tank()
        density = self.company_id.olive_oil_density
        if ctype == 'last':
            compensation_ratio = self.warehouse_id.olive_oil_compensation_ratio
            if compensation_ratio < MIN_RATIO or compensation_ratio > MAX_RATIO:
                raise UserError(_(
                    "The compensation ratio (%s) is not realistic")
                    % compensation_ratio)
            compensation_oil_qty = compensation_ratio * self.compensation_last_olive_qty / 100.0
        elif ctype == 'first':
            compensation_oil_qty =\
                self.compensation_location_id.olive_oil_qty()
        self.write({
            'state': 'ratio',
            'oil_product_id': oil_product.id,
            'compensation_ratio': compensation_ratio,
            'compensation_oil_qty': compensation_oil_qty,
            'compensation_oil_qty_kg': compensation_oil_qty * density,
            })

    def ratio2force(self):
        self.ensure_one()
        assert self.state == 'ratio'
        new_state = 'force'
        if len(self.line_ids) == 1:  # Skip force ratio step
            new_state = 'pack'
            if self.oil_destination == 'sale':  # Skip pack
                new_state = 'check'
        self.write({
            'state': new_state,
            })
        self.set_qty_on_lines()

    def force2pack(self):
        self.ensure_one()
        assert self.state == 'force'
        new_state = 'pack'
        if self.oil_destination == 'sale':  # Skip pack
            new_state = 'check'
        self.write({
            'state': new_state,
            })

    def pack2check(self):
        self.ensure_one()
        assert self.state == 'pack'
        self.write({
            'state': 'check',
            })

    def set_qty_on_lines(self, force_ratio=False):
        """force_ratio=(line_to_force, ratio)
        All pro-rata computation is handled here"""
        self.ensure_one()
        oil_prec = self.env['decimal.precision'].precision_get('Olive Oil Volume')
        ratio_prec = self.env['decimal.precision'].precision_get('Olive Oil Ratio')
        total_oil_qty = self.oil_qty
        ctype = self.compensation_type
        if ctype == 'last':
            total_oil_qty -= self.compensation_oil_qty
        total_compensation_oil_qty = False
        if ctype in ('first', 'last'):
            total_compensation_oil_qty = self.compensation_oil_qty
        if force_ratio:
            first_line_to_process = force_ratio[0]
            first_line_ratio = force_ratio[1]
            first_line_oil_qty = first_line_to_process.olive_qty * first_line_ratio / 100.0
            total_oil_prorata = total_oil_qty - first_line_oil_qty
            total_olive_prorata = self.olive_qty - first_line_to_process.olive_qty
        else:
            first_line_to_process = self.line_ids[0]
            first_line_ratio = self.ratio
            first_line_oil_qty = first_line_to_process.olive_qty * total_oil_qty / self.olive_qty
            total_oil_prorata = total_oil_qty
            total_olive_prorata = self.olive_qty
        first_line_compensation_oil_qty = False
        if total_compensation_oil_qty:
            first_line_compensation_oil_qty = total_compensation_oil_qty * first_line_oil_qty / total_oil_qty

        first_line_vals = first_line_to_process.oil_qty_compute_other_vals(
            first_line_oil_qty, first_line_compensation_oil_qty, first_line_ratio)
        # Write on first line
        first_line_to_process.write(first_line_vals)
        lines = [line for line in self.line_ids if line != first_line_to_process]
        for line in lines:
            # compute oil qty at the pro-rata of olive qty
            oil_qty = line.olive_qty * total_oil_prorata / total_olive_prorata
            ratio = float_round(
                100 * oil_qty / line.olive_qty, precision_digits=ratio_prec)
            compensation_oil_qty = False
            if total_compensation_oil_qty:
                compensation_oil_qty = total_compensation_oil_qty * oil_qty / total_oil_qty,
            vals = line.oil_qty_compute_other_vals(
                oil_qty, compensation_oil_qty, ratio)
            # Write on other lines
            line.write(vals)

    def compensation_check_tank(self):
        self.ensure_one()
        ctype = self.compensation_type
        if ctype not in ('last', 'first'):
            return True
        pr_oil = self.env['decimal.precision'].precision_get('Olive Oil Volume')
        cloc = self.compensation_location_id
        if not cloc:
            raise UserError(_(
                "The production %s uses compensation, so you must set the "
                "compensation tank.") % self.name)
        cqty = cloc.olive_oil_qty()
        if ctype == 'last':
            # cloc must be empty
            if float_compare(cqty, 0, precision_digits=pr_oil) > 0:
                raise UserError(_(
                    "The production %s uses last of day compensation, so the compensation tank must be empty before the operation.") % self.name)
        elif ctype == 'first':
            if float_compare(cqty, 0, precision_digits=pr_oil) <= 0:
                raise UserError(_(
                    "The production %s uses first of day compensation, so the compensation tank mustn't be empty before the operation.") % self.name)


    def check2done(self):
        self.ensure_one()
        assert self.state == 'check'
        splo = self.env['stock.production.lot']
        smo = self.env['stock.move']
        sqo = self.env['stock.quant']
        pr_oli = self.env['decimal.precision'].precision_get('Olive Weight')
        pr_oil = self.env['decimal.precision'].precision_get('Olive Oil Volume')
        wloc = self.warehouse_id.olive_withdrawal_loc_id
        stock_loc = self.warehouse_id.lot_stock_id
        sale_loc = self.sale_location_id
        cloc = self.compensation_location_id
        oil_product = self.oil_product_id
        to_shrinkage_tank_oil_qty = 0.0
        ctype = self.compensation_type

        if self.oil_destination in ('sale', 'mix'):
            if not sale_loc:
                raise UserError(_(
                    "Sale tank is not set on oil production %s.") % self.name)
            if not sale_loc.oil_product_id:
                raise UserError(_(
                    "Oil product not configured on stock location '%s'.")
                    % sale_loc.display_name)
            if sale_loc.oil_product_id != oil_product:
                raise UserError(_(
                    "The production %s is configured to produce "
                    "oil product '%s', but the sale tank '%s' "
                    "is configured with oil product '%s'.") % (
                        self.name, oil_product.display_name,
                        sale_loc.display_name,
                        sale_loc.oil_product_id.display_name))
        self.compensation_check_tank()
        if ctype == 'last':
            if float_compare(self.compensation_oil_qty, 0, precision_digits=pr_oil) <= 0:
                raise UserError(_(
                    "The production %s uses last of day compensation, so the 'Oil Compensation' should be positive.") % self.name)
        for line in self.line_ids:
            # create prod lot
            prodlot = splo.create({
                'arrival_line_id': line.id,
                'product_id': oil_product.id,
                'name': line.name,
                })
            if float_compare(line.withdrawal_oil_qty, 0, precision_digits=pr_oil) > 0:
                # create move from virtual prod > Withdrawal loc
                wmove = smo.create({
                    'product_id': oil_product.id,
                    'name': _('Olive oil production %s: oil withdrawal related to arrival line %s') % (self.name, line.name),
                    'location_id': oil_product.property_stock_production.id,
                    'location_dest_id': wloc.id,
                    'product_uom': oil_product.uom_id.id,
                    'origin': self.name,
                    'product_uom_qty': line.withdrawal_oil_qty,
                    'restrict_lot_id': prodlot.id,
                    'restrict_partner_id': line.partner_id.id,
                    })
                wmove.action_done()
                assert wmove.state == 'done'
                line.withdrawal_move_id = wmove.id
            if float_compare(line.to_sale_tank_oil_qty, 0, precision_digits=pr_oil) > 0:
                # Create move to sale tank
                sale_move = smo.create({
                    'product_id': oil_product.id,
                    'name': _('Olive oil production %s: sale related to arrival line %s') % (self.name, line.name),
                    'location_id': oil_product.property_stock_production.id,
                    'location_dest_id': sale_loc.id,
                    'product_uom': oil_product.uom_id.id,
                    'origin': self.name,
                    'product_uom_qty': line.to_sale_tank_oil_qty,
                    'restrict_lot_id': prodlot.id,
                    })
                sale_move.action_done()
                assert sale_move.state == 'done'
                line.sale_move_id = sale_move.id
            if (
                    ctype == 'last' and
                    float_compare(line.compensation_oil_qty, 0, precision_digits=pr_oil) > 0):
                cmove = smo.create({
                    'product_id': oil_product.id,
                    'name': _('Olive oil production %s: compensation related to arrival line %s') % (self.name, line.name),
                    'location_id': oil_product.property_stock_production.id,
                    'location_dest_id': cloc_id.id,
                    'product_uom': oil_product.uom_id.id,
                    'origin': self.name,
                    'product_uom_qty': line.compensation_oil_qty,
                    'restrict_lot_id': prodlot.id,
                    })
                cmove.action_done()
                assert cmove.state == 'done'
                line.compensation_move_id = cmove.id
                cloc.oil_product_id = oil_product.id

            for extra in line.extra_ids:
                if extra.product_id.tracking and extra.product_id.tracking != 'none':
                    raise UserError(_(
                        "Can't select the product '%s' in extra items of "
                        "line %s because it is tracked by lot or serial.")
                        % (extra.product_id.display_name, line.name))
                extra_move = smo.create({
                    'product_id': extra.product_id.id,
                    'name': _('Olive oil production %s: extra item withdrawal related to arrival line %s') % (self.name, line.name),
                    'location_id': stock_loc_id,
                    'location_dest_id': wloc.id,
                    'product_uom': extra.product_id.uom_id.id,
                    'origin': self.name,
                    'product_uom_qty': extra.qty,
                    'restrict_partner_id': line.partner_id.id,
                    })
                extra_move.action_done()
                assert extra_move.state == 'done'
            if line.oil_destination == 'withdrawal':
                to_shrinkage_tank_oil_qty += line.shrinkage_oil_qty
        if not oil_product.shrinkage_prodlot_id:
            raise UserError(_(
                "Missing shrinkage production lot on product '%s'.")
                % oil_product.display_name)
        prod_vals = {
            'state': 'done',
            'done_datetime': fields.Datetime.now(),
            }
        if float_compare(to_shrinkage_tank_oil_qty, 0, precision_digits=pr_oil) > 0:
            shrinkage_move = smo.create({
                'product_id': oil_product.id,
                'name': _('Olive Oil Production %s: Shrinkage') % self.name,
                'location_id': oil_product.property_stock_production.id,
                'location_dest_id': self.warehouse_id.olive_shrinkage_loc_id.id,
                'product_uom': oil_product.uom_id.id,
                'origin': self.name,
                'product_uom_qty': to_shrinkage_tank_oil_qty,
                'restrict_lot_id': oil_product.shrinkage_prodlot_id.id,
                })
            shrinkage_move.action_done()
            prod_vals['shrinkage_move_id'] = shrinkage_move.id
        if ctype == 'first':
            if self.oil_destination == 'sale':
                if not self.compensation_sale_location_id:
                    raise UserError(_(
                        "On oil production %s which has first-of-day "
                        "compensation, you must set a compensation sale tank.") % self.name)
                if self.compensation_sale_location_id.oil_product_id != self.oil_product_id:
                    raise UserError(_(
                        "On oil production %s, you must select a compensation "
                        "tank with an olive type %s.") % (
                            self.name, self.oil_product_id.display_name))
                cloc.olive_oil_transfer(
                    self.compensation_sale_location_id, 'full', self.warehouse_id,
                    origin=_('Empty compensation tank to sale tank'), auto_validate=True)
            elif self.oil_destination == 'withdrawal' and len(self.line_ids) == 1:
                cloc.olive_oil_transfer(
                    wloc, 'full', self.warehouse_id,
                    origin=_('Empty compensation tank to withdrawal location'),
                    auto_validate=True)
            else:
                raise UserError(_(
                    "This first-of-day compensation scenario is not implemented yet"))
            cloc.oil_product_id = False

        self.write(prod_vals)
        # Free the palox
        self.palox_id.oil_product_id = False

    def unlink(self):
        for production in self:
            if production.state == 'done':
                raise UserError(_(
                    "Cannot delete production %s which is in Done state.")
                    % production.name)
        return super(OliveOilProduction, self).unlink()
