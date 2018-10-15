# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero, float_round
from odoo.tools.misc import formatLang
from babel.dates import format_date
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
        related='partner_id.olive_culture_type', readonly=True,
        compute_sudo=True)
    organic_palox_required = fields.Boolean(
        compute='_compute_organic_palox_required', readonly=True, store=True,
        compute_sudo=True)
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
    default_leaf_removal = fields.Boolean(
        string='Default Leaf Removal',
        states={'done': [('readonly', True)]})
    olive_qty = fields.Float(
        compute='_compute_olive_qty', readonly=True, store=True,
        track_visibility='onchange', string='Total Quantity (kg)',
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
        help="Select returned palox other than those used in the arrival "
        "lines")

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
        res = self.env['olive.arrival.line'].read_group(
            [('arrival_id', 'in', self.ids)],
            ['arrival_id', 'olive_qty'], ['arrival_id'])
        for re in res:
            self.browse(re['arrival_id'][0]).olive_qty = re['olive_qty']

    @api.onchange('partner_id')
    def partner_id_change(self):
        if self.partner_id:
            ochards = self.env['olive.ochard'].search([
                ('partner_id', '=', self.partner_id.id)])
            if len(ochards) == 1:
                self.default_ochard_id = ochards
        else:
            self.default_ochard_id = False

    @api.depends('partner_id.olive_culture_type')
    def _compute_organic_palox_required(self):
        for line in self:
            organic_palox_required = False
            if line.partner_id.olive_culture_type in ('organic', 'conversion'):
                organic_palox_required = True
            line.organic_palox_required = organic_palox_required

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'olive.arrival')
        return super(OliveArrival, self).create(vals)

    def cancel(self):
        for arrival in self:
            if (
                    arrival.state == 'done' and
                    any([line.production_id for line in arrival.line_ids])):
                raise UserError(_(
                    "Cannot cancel arrival %s because it has lines already "
                    "selected in a production.") % arrival.name)
        self.write({'state': 'cancel'})

    def back2draft(self):
        for arrival in self:
            assert arrival.state == 'cancel'
        self.write({'state': 'draft'})

    def validate(self):
        self.ensure_one()
        assert self.state == 'draft'
        oalo = self.env['olive.arrival.line']
        if not self.line_ids:
            raise UserError(_(
                "Missing lines on arrival '%s'.") % self.name)
        oalo = self.env['olive.arrival.line']
        pr_oli = self.env['decimal.precision'].precision_get('Olive Weight')
        pr_oil = self.env['decimal.precision'].precision_get(
            'Olive Oil Volume')
        lended_case_id = False
        if self.returned_case or self.returned_organic_case:
            if self.returned_case > self.partner_id.olive_lended_case:
                raise UserError(_(
                    "The olive farmer '%s' currently has %d lended case(s) "
                    "and the olive arrival %s declares %d returned case(s).")
                    % (self.partner_id.display_name,
                       self.partner_id.olive_lended_case,
                       self.name,
                       self.returned_case))
            if (self.returned_organic_case >
                    self.partner_id.olive_lended_organic_case):
                raise UserError(_(
                    "The olive farmer '%s' currently has %d lended organic "
                    "case(s) and the olive arrival %s declares %d returned "
                    "organic case(s).") % (
                        self.partner_id.display_name,
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
        palox_max_weight = self.company_id.olive_max_qty_per_palox
        for line in self.line_ids:
            if float_is_zero(line.olive_qty, precision_digits=pr_oli):
                raise UserError(_(
                    "On line %s, the olive quantity is null")
                    % line.name)
            if line.palox_id.borrower_partner_id:
                returned_palox |= line.palox_id
            for palox in self.returned_palox_ids:
                returned_palox |= palox
            # Block if oil_product is not coherent with partner (organic, ...)
            if (line.oil_product_id.olive_culture_type !=
                    partner_olive_culture_type):
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
                    float_is_zero(
                        line.mix_withdrawal_oil_qty, precision_digits=pr_oil)):
                raise UserError(_(
                    "On line %s, the oil destination is 'mix' so you must "
                    "enter the requested withdrawal qty") % line.name)
            # Block if palox under production
            same_palox_under_production = oalo.search([
                ('palox_id', '=', line.palox_id.id),
                ('arrival_state', '=', 'done'),
                ('production_id', '!=', False),
                ('production_state', 'not in', ('done', 'cancel')),
                ], limit=1)
            if same_palox_under_production:
                raise UserError(_(
                    "You are collecting in palox %s which is currently under "
                    "production (%s). You should finish or cancel this "
                    "production first.") % (
                        line.palox_id.name,
                        same_palox_under_production.production_id.name))

            # Check if palox is organic
            if (
                    partner_olive_culture_type in
                    ('organic', 'conversion') and
                    not line.palox_id.organic):
                raise UserError(_(
                    "You are collecting %s in palox %s which is not an "
                    "organic palox.") % (
                        line.oil_product_id.name,
                        line.palox_id.name))

            # Check oil product is the same
            if not line.palox_id.oil_product_id:
                line.palox_id.oil_product_id = line.oil_product_id.id
            elif line.palox_id.oil_product_id != line.oil_product_id:
                raise UserError(_(
                    "You are collecting %s in palox %s but this palox "
                    "currently has %s.") % (
                        line.oil_product_id.name,
                        line.palox_id.name,
                        line.palox_id.oil_product_id.name))

            # Check palox max qty
            new_weight = line.palox_id.weight + line.olive_qty
            if new_weight > palox_max_weight:
                raise UserError(_(
                    "With this arrival, the palox %s would weight %s kg, "
                    "which is over the maximum weight for a palox "
                    "(%s kg).") % (
                        line.palox_id.name, new_weight, palox_max_weight))

            # TODO MIX : coherence qté retrait et qté olive

            # Warn if not same variant
            same_palox_different_variant = oalo.search([
                ('palox_id', '=', line.palox_id.id),
                ('arrival_state', '=', 'done'),
                ('production_id', '=', False),
                ('variant_id', '!=', line.variant_id.id)])
            if same_palox_different_variant:
                msg = _(
                    "You are putting %s in palox %s but arrival line %s "
                    "in the same palox has %s") % (
                        line.variant_id.display_name,
                        line.palox_id.name,
                        same_palox_different_variant[0].name,
                        same_palox_different_variant[0].variant_id.name)
                self.env.user.notify_warning(msg)
                self.message_post(msg)

            # Warn if not same oil destination
            same_palox_different_oil_destination = oalo.search([
                ('palox_id', '=', line.palox_id.id),
                ('arrival_state', '=', 'done'),
                ('production_id', '=', False),
                ('oil_destination', '!=', line.oil_destination)])
            if same_palox_different_oil_destination:
                msg = _(
                    "You selected %s for palox %s but arrival line %s in "
                    "the same palox has %s") % (
                        line.oil_destination,
                        line.palox_id.name,
                        same_palox_different_oil_destination[0].display_name,
                        same_palox_different_oil_destination[0].oil_destination)
                self.env.user.notify_warning(msg)
                self.message_post(msg)
        # Mark palox as returned
        returned_palox.write({
            'borrower_partner_id': False,
            'borrowed_date': False,
            })
        # TODO : check that we don't overload a palox
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
        string='Arrival Line Number', required=True, readonly=True,
        default='/')
    arrival_id = fields.Many2one(
        'olive.arrival', string='Arrival', ondelete='cascade')
    company_id = fields.Many2one(
        related='arrival_id.company_id', store=True, readonly=True)
    arrival_state = fields.Selection(
        related='arrival_id.state', string='Arrival State',
        readonly=True, store=True)
    arrival_date = fields.Date(
        related='arrival_id.date', readonly=True, store=True)
    season_id = fields.Many2one(
        related='arrival_id.season_id', readonly=True, store=True)
    warehouse_id = fields.Many2one(
        related='arrival_id.warehouse_id', readonly=True, store=True)
    partner_id = fields.Many2one(
        related='arrival_id.partner_id', string='Olive Farmer',
        readonly=True, store=True)
    partner_olive_culture_type = fields.Selection(
        related='arrival_id.partner_id.olive_culture_type',
        readonly=True, store=True)
    leaf_removal = fields.Boolean(string='Leaf Removal')
    variant_id = fields.Many2one(
        'olive.variant', string='Olive Variant', required=True)
    olive_qty = fields.Float(
        string='Olive Qty (kg)', help="Olive Quantity in Kg", required=True,
        digits=dp.get_precision('Olive Weight'))
    ochard_id = fields.Many2one(
        'olive.ochard', string='Ochard', required=True)
    palox_id = fields.Many2one(
        'olive.palox', string='Palox', required=True)
    organic_palox_required = fields.Boolean(
        related='arrival_id.organic_palox_required', readonly=True,
        required=True)
    oil_destination = fields.Selection([
        ('withdrawal', 'Withdrawal'),
        ('sale', 'Sale'),
        ('mix', 'Mix'),
        ], string='Oil Destination', required=True)
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
    production_date = fields.Date(
        related='production_id.date', string='Production Date', readonly=True,
        store=True)
    production_state = fields.Selection(
        related='production_id.state', string='Production State',
        readonly=True, store=True)
    oil_ratio = fields.Float(
        string='Oil Ratio (%)', digits=dp.get_precision('Olive Oil Ratio'),
        readonly=True)
    oil_ratio_net = fields.Float(
        string='Oil Net Ratio (%)', digits=dp.get_precision('Olive Oil Ratio'),
        readonly=True)
    extra_ids = fields.One2many(
        'olive.arrival.line.extra', 'line_id', string="Extra Items")
    extra_count = fields.Integer(
        compute='_compute_extra_count', string='Extra Items Lines', readonly=True)

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

    shrinkage_oil_qty = fields.Float(  # Sale and withdraw
        readonly=True, digits=dp.get_precision('Olive Oil Volume'))
    shrinkage_oil_qty_kg = fields.Float(  # Withdraw only
        readonly=True, digits=dp.get_precision('Olive Weight'))

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
    sale_oil_qty = fields.Float(
        readonly=True, digits=dp.get_precision('Olive Oil Volume'))
    filter_loss_oil_qty = fields.Float(
        readonly=True, digits=dp.get_precision('Olive Oil Volume'))
    sale_without_shrinkage_oil_qty = fields.Float(
        readonly=True, digits=dp.get_precision('Olive Oil Volume'))
    # Invoicing
    out_invoice_id = fields.Many2one('account.invoice', readonly=True)
    in_invoice_id = fields.Many2one('account.invoice', readonly=True)

    _sql_constraints = [(
        'olive_qty_positive',
        'CHECK(olive_qty >= 0)',
        'The olive quantity must be positive or 0.'), (
        'mix_withdrawal_oil_qty_qty_positive',
        'CHECK(mix_withdrawal_oil_qty >= 0)',
        'The requested withdrawal qty must be positive or 0.'),
        ]

    @api.depends('extra_ids')
    def _compute_extra_count(self):
        res = self.env['olive.arrival.line.extra'].read_group(
            [('line_id', 'in', self.ids)], ['line_id'], ['line_id'])
        print "_compute_extra_count res=", res
        for re in res:
            self.browse(re['line_id'][0]).extra_count = re['line_id_count']

    @api.onchange('oil_destination')
    def oil_destination_change(self):
        if self.oil_destination != 'mix':
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

    def oil_qty_compute_other_vals(self, oil_qty, ratio):
        pr_oil = self.env['decimal.precision'].precision_get(
            'Olive Oil Volume')
        pr_oli = self.env['decimal.precision'].precision_get('Olive Weight')
        pr_ratio = self.env['decimal.precision'].precision_get(
            'Olive Oil Ratio')
        company = self.production_id.company_id
        density = company.olive_oil_density
        shrinkage_ratio = company.olive_shrinkage_ratio
        filter_ratio = company.olive_filter_ratio
        oil_destination = self.oil_destination
        if not density:
            raise UserError(_(
                "Missing Olive Oil Density on company '%s'")
                % company.display_name)
        # oil_qty = float_round(oil_qty, precision_digits=oil_prec)
        oil_qty_kg = float_round(
            oil_qty * density, precision_digits=pr_oli)
        withdrawal_oil_qty = withdrawal_oil_qty_kg = filter_loss_oil_qty = 0.0
        sale_oil_qty = to_sale_tank_oil_qty = ratio_net = 0.0
        shrinkage_oil_qty = float_round(
            oil_qty * shrinkage_ratio / 100, precision_digits=pr_oil)
        shrinkage_oil_qty_kg = float_round(
            shrinkage_oil_qty * density, precision_digits=pr_oli)
        oil_minus_shrinkage = oil_qty - shrinkage_oil_qty
        if oil_destination == 'withdrawal':
            withdrawal_oil_qty = float_round(
                oil_minus_shrinkage, precision_digits=pr_oil)
            withdrawal_oil_qty_kg = float_round(
                oil_qty_kg - shrinkage_oil_qty_kg, precision_digits=pr_oli)

        elif oil_destination == 'sale':
            filter_loss_oil_qty = oil_qty * filter_ratio / 100
            sale_oil_qty = oil_minus_shrinkage - filter_loss_oil_qty
            to_sale_tank_oil_qty = oil_qty - filter_loss_oil_qty

        elif oil_destination == 'mix':
            if float_compare(
                    oil_minus_shrinkage, self.mix_withdrawal_oil_qty,
                    precision_digits=pr_oil) >= 0:
                withdrawal_oil_qty = self.mix_withdrawal_oil_qty
                oil_qty_minus_withdrawal = oil_qty - withdrawal_oil_qty
                filter_loss_oil_qty = \
                    oil_qty_minus_withdrawal * filter_ratio / 100
                sale_oil_qty = oil_qty_minus_withdrawal \
                    - shrinkage_oil_qty - filter_loss_oil_qty
                to_sale_tank_oil_qty = oil_qty_minus_withdrawal \
                    - filter_loss_oil_qty
            else:
                withdrawal_oil_qty = oil_minus_shrinkage
                # rewrite oil destination, for shrinkage stock move
                oil_destination = 'withdrawal'
            withdrawal_oil_qty_kg = withdrawal_oil_qty * density
        ratio_net = float_round(
            100 * (oil_minus_shrinkage - filter_loss_oil_qty) / self.olive_qty,
            precision_digits=pr_ratio)

        vals = {
            'oil_qty_kg': oil_qty_kg,
            'oil_qty': oil_qty,
            'oil_ratio': ratio,
            'oil_ratio_net': ratio_net,
            'shrinkage_oil_qty': shrinkage_oil_qty,
            'shrinkage_oil_qty_kg': shrinkage_oil_qty_kg,
            'withdrawal_oil_qty_kg': withdrawal_oil_qty_kg,
            'withdrawal_oil_qty': withdrawal_oil_qty,
            'oil_destination': oil_destination,
            'filter_loss_oil_qty': filter_loss_oil_qty,
            'sale_oil_qty': sale_oil_qty,
            'to_sale_tank_oil_qty': to_sale_tank_oil_qty,
            }
        return vals

    def pre_prepare_invoice_line(self, product, invoice_vals):
        ailo = self.env['account.invoice.line']
        il_vals = {
            'product_id': product.id,
            'invoice_id': invoice_vals,
            }
        il_vals = ailo.play_onchanges(il_vals, ['product_id'])
        il_vals.pop('invoice_id')
        return il_vals

    def prepare_invoice(self, invoice_type, invoice_reference=False):
        pr_oil = self.env['decimal.precision'].precision_get(
            'Olive Oil Volume')
        pr_oli = self.env['decimal.precision'].precision_get('Olive Weight')
        pr_tax = self.env['decimal.precision'].precision_get(
            'Olive Oil Tax Price Unit')
        pr_pri = self.env['decimal.precision'].precision_get(
            'Product Price')
        aio = self.env['account.invoice']
        pplo = self.env['product.pricelist']
        ppo = self.env['product.product']
        partner = self[0].partner_id.commercial_partner_id
        company = self.env.user.company_id
        origin = [line.name for line in self]
        if len(origin) > 3:
            origin = origin[:3] + ['...']
        origin = ', '.join(origin)
        pricelist = partner.property_product_pricelist
        currency = pricelist.currency_id
        vals = {
            'partner_id': partner.id,
            'currency_id': currency.id,
            'type': invoice_type,
            'company_id': company.id,
            'origin': origin,
            'reference': invoice_reference,
            'invoice_line_ids': [],
        }
        vals = aio.play_onchanges(vals, ['partner_id'])
        if invoice_type == 'in_invoice':
            for line in self:
                if float_compare(
                        line.sale_oil_qty, 0, precision_digits=pr_oli) <= 0:
                    continue
                il_vals = self.pre_prepare_invoice_line(
                    line.oil_product_id, vals)
                il_vals['origin'] = line.name
                arrival_date_formatted = format_date(
                    fields.Date.from_string(line.arrival_date),
                    format='short', locale=self.env.user.lang or 'en_US')
                il_vals['name'] += _(
                    ' (Arrival Line %s dated %s)') % (
                        line.name, arrival_date_formatted)
                il_vals['quantity'] = line.sale_oil_qty
                il_vals['price_unit'] = 10.0
                vals['invoice_line_ids'].append((0, 0, il_vals))
        elif invoice_type == 'out_invoice':
            season = self[0].season_id
            totals = self.read_group(
                [('id', 'in', self.ids)],
                ['olive_qty', 'oil_qty', 'shrinkage_oil_qty',
                 'filter_loss_oil_qty'], [])[0]
            if float_compare(
                    totals['oil_qty'], 0, precision_digits=pr_oil) <= 0:
                return False
            if not company.olive_oil_production_product_id:
                raise UserError(_(
                    "Missing Production Product on company %s.")
                    % company.name)
            if not company.olive_oil_leaf_removal_product_id:
                raise UserError(_(
                    "Missing leaf removal product on company %s")
                    % company.name)
            if not company.olive_oil_tax_product_id:
                raise UserError(_(
                    "Missing Tax Product on company %s.") % company.name)
            # Production
            il_vals = self.pre_prepare_invoice_line(
                company.olive_oil_production_product_id, vals)
            il_vals['quantity'] = totals['olive_qty']
            il_vals['price_unit'] = pricelist.get_product_price(
                company.olive_oil_production_product_id,
                totals['olive_qty'], partner)
            vals['invoice_line_ids'].append((0, 0, il_vals))
            # Discount
            if season.early_bird_date:
                total_disc = self.read_group(
                    [('id', 'in', self.ids),
                     ('arrival_date', '<=', season.early_bird_date)],
                    ['olive_qty'], [])[0]
                if float_compare(
                        total_disc['olive_qty'], 0,
                        precision_digits=pr_oli) > 0:
                    il_vals = self.pre_prepare_invoice_line(
                        company.olive_oil_early_bird_discount_product_id, vals)
                    # with Factur-X, we can't have negative prices
                    # so I put a negative qty
                    il_vals['quantity'] = total_disc['olive_qty'] * -1
                    il_vals['price_unit'] = pricelist.get_product_price(
                        company.olive_oil_early_bird_discount_product_id,
                        total_disc['olive_qty'], partner)
                    vals['invoice_line_ids'].append((0, 0, il_vals))
            # leaf removal
            total_leaf = self.read_group(
                [('id', 'in', self.ids), ('leaf_removal', '=', True)],
                ['olive_qty'], [])[0]
            if (
                    total_leaf['olive_qty'] and
                    float_compare(
                        total_leaf['olive_qty'], 0,
                        precision_digits=pr_oli) > 0):
                il_vals = self.pre_prepare_invoice_line(
                    company.olive_oil_leaf_removal_product_id, vals)
                il_vals['quantity'] = total_leaf['olive_qty']
                il_vals['price_unit'] = pricelist.get_product_price(
                    company.olive_oil_leaf_removal_product_id,
                    total_leaf['olive_qty'], partner)
                vals['invoice_line_ids'].append((0, 0, il_vals))
            # AFIDOL Tax
            il_vals = self.pre_prepare_invoice_line(
                company.olive_oil_tax_product_id, vals)
            qty = totals['oil_qty'] - totals['shrinkage_oil_qty']\
                - totals['filter_loss_oil_qty']
            if float_is_zero(company.olive_oil_tax_price_unit, precision_digits=pr_tax):
                price_unit = pricelist.get_product_price(
                    company.olive_oil_tax_product_id, qty, partner)
            else:
                price_unit = company.olive_oil_tax_price_unit
            if pr_tax > pr_pri:
                il_vals['quantity'] = 1
                il_vals['price_unit'] = float_round(
                    price_unit * qty, precision_rounding=currency.rounding)
                qty_formatted = formatLang(
                    self.env, qty, dp='Olive Oil Volume')
                price_unit_formatted = formatLang(
                    self.env, price_unit, dp='Olive Oil Tax Price Unit')
                il_vals['name'] += _(u" (%s L x %s %s / L)") % (
                    qty_formatted, price_unit_formatted, currency.symbol)
            else:
                il_vals['quantity'] = qty
                il_vals['price_unit'] = price_unit
            vals['invoice_line_ids'].append((0, 0, il_vals))
            # Extra items
            extra_totals = self.env['olive.arrival.line.extra'].read_group(
                [('line_id', 'in', self.ids)],
                ['product_id', 'qty'], ['product_id'])
            for extra_total in extra_totals:
                product_id = extra_total['product_id'][0]
                product = ppo.browse(product_id)
                qty = extra_total['qty']
                il_vals = self.pre_prepare_invoice_line(product, vals)
                il_vals['quantity'] = qty
                il_vals['price_unit'] = pricelist.get_product_price(
                    product, qty, partner)
                vals['invoice_line_ids'].append((0, 0, il_vals))
        return vals

    def in_invoice_create(self):
        aio = self.env['account.invoice']
        vals = self.prepare_invoice('in_invoice')
        if vals and vals['invoice_line_ids']:
            invoice = aio.with_context(type='in_invoice').create(vals)
            self.write({'in_invoice_id': invoice.id})
        return invoice

    def out_invoice_create(self):
        aio = self.env['account.invoice']
        vals = self.prepare_invoice('out_invoice')
        if vals and vals['invoice_line_ids']:
            invoice = aio.with_context(type='out_invoice').create(vals)
            self.write({'out_invoice_id': invoice.id})
        return invoice


class OliveArrivalLineExtra(models.Model):
    _name = 'olive.arrival.line.extra'
    _description = 'Extra items linked to the arrival line'

    line_id = fields.Many2one(
        'olive.arrival.line', string='Arrival Line', ondelete='cascade')
    product_id = fields.Many2one(
        'product.product', string='Extra Product',
        required=True, ondelete='restrict',
        domain=[
            ('type', 'in', ('product', 'consu')),
            '|', ('tracking', '=', False), ('tracking', '=', 'none')])
    qty = fields.Float(
        string='Quantity', default=1,
        digits=dp.get_precision('Product Unit of Measure'), required=True)
    uom_id = fields.Many2one(
        related='product_id.uom_id', readonly=True)
