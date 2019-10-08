# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
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
        'olive.season', string='Season', required=True, index=True,
        default=lambda self: self.env.user.company_id.current_season_id.id,
        states={'done': [('readonly', True)]})
    partner_id = fields.Many2one(
        'res.partner', string='Olive Farmer', required=True, index=True,
        domain=[('parent_id', '=', False), ('olive_farmer', '=', True)],
        states={'done': [('readonly', True)]},
        track_visibility='onchange')
    commercial_partner_id = fields.Many2one(
        related='partner_id.commercial_partner_id', readonly=True, store=True)
    partner_organic_certified_logo = fields.Binary(
        related='partner_id.commercial_partner_id.olive_organic_certified_logo',
        readonly=True)
    partner_olive_culture_type = fields.Selection(
        related='partner_id.commercial_partner_id.olive_culture_type', readonly=True)
    partner_olive_cultivation_form = fields.Boolean(
        related='partner_id.commercial_partner_id.olive_cultivation_form',
        readonly=True)
    partner_olive_tree_total = fields.Integer(
        related='partner_id.commercial_partner_id.olive_tree_total',
        readonly=True)
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse', required=True, index=True,
        domain=[('olive_mill', '=', True)],
        default=lambda self: self.env.user._default_olive_mill_wh(),
        states={'done': [('readonly', True)]},
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
        default=fields.Date.context_today, required=True,
        states={'done': [('readonly', True)]})
    harvest_start_date = fields.Date(
        string='Harvest Start Date', required=True,
        states={'done': [('readonly', True)]})
    done_datetime = fields.Datetime(string='Date Done', readonly=True)
    line_ids = fields.One2many(
        'olive.arrival.line', 'arrival_id', string='Arrival Lines',
        states={'done': [('readonly', True)]})
    returned_regular_case = fields.Integer(
        string='Returned Regular Cases', states={'done': [('readonly', True)]})
    returned_organic_case = fields.Integer(
        string='Returned Organic Cases', states={'done': [('readonly', True)]})
    lended_case_id = fields.Many2one(
        'olive.lended.case', string='Lended Case Move', readonly=True)
    returned_palox_ids = fields.Many2many(
        'olive.palox', string='Other Returned Palox',
        states={'done': [('readonly', True)]},
        help="Select returned palox other than those used in the arrival "
        "lines")
    olive_qty_pressed = fields.Float(
        string='Olive Qty Pressed (kg)',
        digits=dp.get_precision('Olive Weight'), readonly=True)
    oil_qty_net = fields.Float(
        string='Net Oil Qty (L)',
        readonly=True, digits=dp.get_precision('Olive Oil Volume'),
        help="Net oil quantity produced in liters."
        "\nFirst-of-day compensation: included."
        "\nLast-of-day compensation: already deducted."
        "\nShrinkage: already deducted."
        "\nFilter loss: already deducted.")
    oil_ratio_net = fields.Float(
        string='Oil Net Ratio (% L)', digits=dp.get_precision('Olive Oil Ratio'),
        readonly=True)
    olive_ratio_net = fields.Float(
        string='Olive Net Ratio (kg / L)', digits=(16, 2),
        readonly=True)

    _sql_constraints = [(
        'returned_regular_case_positive',
        'CHECK(returned_regular_case >= 0)',
        'The returned regular cases must be positive or null.'), (
        'returned_organic_case_positive',
        'CHECK(returned_organic_case >= 0)',
        'The returned organic cases must be positive or null.')]

    @api.depends('line_ids.olive_qty')
    def _compute_olive_qty(self):
        res = self.env['olive.arrival.line'].read_group(
            [('arrival_id', 'in', self.ids)],
            ['arrival_id', 'olive_qty'], ['arrival_id'])
        for re in res:
            self.browse(re['arrival_id'][0]).olive_qty = re['olive_qty']

    @api.constrains('date', 'harvest_start_date')
    def arrival_check(self):
        for arrival in self:
            if arrival.harvest_start_date > arrival.date:
                raise ValidationError(_(
                    "On arrival %s, the harvest start date (%s) cannot be "
                    "after the arrival date (%s)!") % (
                        arrival.name, arrival.harvest_start_date,
                        arrival.date))

    @api.onchange('partner_id')
    def partner_id_change(self):
        if self.partner_id:
            ochards = self.env['olive.ochard'].search([
                ('partner_id', '=', self.commercial_partner_id.id)])
            if len(ochards) == 1:
                self.default_ochard_id = ochards
        else:
            self.default_ochard_id = False

    @api.onchange('default_ochard_id')
    def default_ochard_id_change(self):
        variant = False
        if self.default_ochard_id:
            ochard = self.default_ochard_id
            if len(ochard.parcel_ids) == 1 and len(ochard.parcel_ids[0].variant_ids) == 1:
                variant = ochard.parcel_ids[0].variant_ids[0]
        self.default_variant_id = variant

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'olive.arrival')
        return super(OliveArrival, self).create(vals)

    def cancel(self):
        for arrival in self:
            if all([line.production_id for line in arrival.line_ids]):
                raise UserError(_(
                    "Cannot cancel arrival %s because all its lines are "
                    "currently selected in productions.") % arrival.name)
            arrival.line_ids.filtered(
                lambda l: not l.production_id).write({'state': 'cancel'})
        self.write({'state': 'cancel'})

    def back2draft(self):
        for arrival in self:
            assert arrival.state == 'cancel'
            arrival.line_ids.filtered(
                lambda l: l.state == 'cancel').write({'state': 'draft'})
        self.write({'state': 'draft'})

    def validate(self):
        self.ensure_one()
        assert self.state == 'draft'
        oalo = self.env['olive.arrival.line']
        olco = self.env['olive.lended.case']
        if not self.line_ids:
            raise UserError(_(
                "Missing lines on arrival '%s'.") % self.name)
        oalo = self.env['olive.arrival.line']
        ooao = self.env['olive.oil.analysis']
        pr_oli = self.env['decimal.precision'].precision_get('Olive Weight')
        pr_oil = self.env['decimal.precision'].precision_get(
            'Olive Oil Volume')
        wh = self.warehouse_id
        partner_olive_culture_type = self.commercial_partner_id.olive_culture_type
        palox_max_weight = self.company_id.olive_max_qty_per_palox
        arrival_vals = {
            'state': 'done',
            'done_datetime': fields.Datetime.now(),
            }
        i = 0
        warn_msgs = []
        returned_palox = self.env['olive.palox']
        has_sale_or_mix = False
        for line in self.line_ids:
            i += 1
            if float_is_zero(line.olive_qty, precision_digits=pr_oli):
                raise UserError(_(
                    "On arrival line number %d, the olive quantity is null.")
                    % i)
            if line.oil_destination in ('sale', 'mix'):
                has_sale_or_mix = True
            if line.palox_id.borrower_partner_id:
                returned_palox |= line.palox_id
            for palox in self.returned_palox_ids:
                returned_palox |= palox
            # Block if oil_product is not coherent with partner (organic, ...)
            if (line.oil_product_id.olive_culture_type !=
                    partner_olive_culture_type):
                raise UserError(_(
                    "On arrival line number %d, the destination oil '%s' is "
                    "'%s' but the farmer '%s' is '%s'.") % (
                        i,
                        line.oil_product_id.name,
                        line.oil_product_id.olive_culture_type,
                        self.commercial_partner_id.display_name,
                        partner_olive_culture_type,
                        ))
            if (
                    line.oil_destination == 'mix' and
                    float_is_zero(
                        line.mix_withdrawal_oil_qty, precision_digits=pr_oil)):
                raise UserError(_(
                    "On arrival line number %d, the oil destination is 'mix' "
                    "so you must enter the requested withdrawal qty") % i)

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

            # Warn palox max qty
            new_weight = line.palox_id.weight + line.olive_qty
            if new_weight > palox_max_weight:
                raise UserError(_(
                    "With this arrival, the palox %s would weight %s kg, "
                    "which is over the maximum weight for a palox "
                    "(%s kg).") % (
                        line.palox_id.name, new_weight, palox_max_weight))

            if (
                    line.oil_destination == 'mix' and
                    line.mix_withdrawal_oil_qty > wh.olive_oil_compensation_ratio * line.olive_qty / 100.0):
                warn_msgs.append(_(
                    "On arrival line number %d that has a mixed oil "
                    "destination, the requested withdraway quantity "
                    "(%s L) is superior to the olive quantity of the "
                    "line (%s kg) multiplied by the average ratio "
                    "(%s %%).") % (
                        i, line.mix_withdrawal_oil_qty,
                        line.olive_qty, wh.olive_oil_compensation_ratio))

            # Warn if not same variant
            same_palox_different_variant = oalo.search([
                ('palox_id', '=', line.palox_id.id),
                ('state', '=', 'done'),
                ('production_id', '=', False),
                ('variant_id', '!=', line.variant_id.id)])
            if same_palox_different_variant:
                warn_msgs.append(_(
                    "You are putting %s in palox %s but arrival line %s "
                    "in the same palox has %s.") % (
                        line.variant_id.display_name,
                        line.palox_id.name,
                        same_palox_different_variant[0].name,
                        same_palox_different_variant[0].variant_id.name))

            # Warn if not same oil destination
            same_palox_different_oil_destination = oalo.search([
                ('palox_id', '=', line.palox_id.id),
                ('state', '=', 'done'),
                ('production_id', '=', False),
                ('oil_destination', '!=', line.oil_destination)])
            if same_palox_different_oil_destination:
                fg = dict(oalo.fields_get(
                    'oil_destination', 'selection')['oil_destination']['selection'])
                warn_msgs.append(_(
                    "You selected '%s' for palox %s but arrival line %s in "
                    "the same palox has '%s'.") % (
                        fg[line.oil_destination],
                        line.palox_id.name,
                        same_palox_different_oil_destination[0].display_name,
                        fg[same_palox_different_oil_destination[0].oil_destination]))

            # Create analysis
            ana_products = self.env['product.product']
            for extra in line.extra_ids.filtered(lambda x: x.product_id.olive_type == 'analysis'):
                ana_products |= extra.product_id
            if ana_products:
                existing_ana = ooao.search(
                    [('arrival_line_id', '=', line.id)], limit=1)
                if not existing_ana:
                    ana_vals = {
                        'arrival_line_id': line.id,
                        'line_ids': [],
                        }
                    for ana_product in ana_products:
                        ana_vals['line_ids'].append((0, 0, {'product_id': ana_product.id}))
                    ooao.create(ana_vals)

            # Set line number
            line.write({
                'name': '%s/%s' % (self.name, i),
                })

        # for mix/sale, warn if delay between harvest and arrival is too long
        arrival_date_dt = fields.Date.from_string(self.date)
        harvest_st_date_dt = fields.Date.from_string(self.harvest_start_date)
        delta_days = (arrival_date_dt - harvest_st_date_dt).days
        max_delta_days = self.company_id.olive_harvest_arrival_max_delta_days
        if has_sale_or_mix and delta_days > max_delta_days:
            warn_msgs.append(_(
                "This arrival has sale or mix oil destination and the delay "
                "between the harvest start date (%s) and the arrival date "
                "(%s) is %d days (maximum allowed is %d days).") % (
                    self.harvest_start_date, self.date,
                    delta_days, max_delta_days))
        if warn_msgs:
            if not self._context.get('olive_no_warning'):
                action = self.env['ir.actions.act_window'].for_xml_id(
                    'olive_mill', 'olive_arrival_warning_action')
                action['context'] = {
                    'default_arrival_id': self.id,
                    'default_msg': '\n\n'.join(warn_msgs),
                    'default_count': len(warn_msgs),
                    }
                return action
            else:
                for warn_msg in warn_msgs:
                    self.message_post(warn_msg)

        if self.returned_regular_case or self.returned_organic_case:
            if (
                    not self.lended_case_id and
                    self.returned_regular_case > self.commercial_partner_id.olive_lended_regular_case):
                raise UserError(_(
                    "The olive farmer '%s' currently has %d lended case(s) "
                    "but the olive arrival %s declares %d returned case(s).")
                    % (self.commercial_partner_id.display_name,
                       self.commercial_partner_id.olive_lended_regular_case,
                       self.name,
                       self.returned_regular_case))
            if (
                    not self.lended_case_id and
                    self.returned_organic_case >
                    self.commercial_partner_id.olive_lended_organic_case):
                raise UserError(_(
                    "The olive farmer '%s' currently has %d lended organic "
                    "case(s) but the olive arrival %s declares %d returned "
                    "organic case(s).") % (
                        self.commercial_partner_id.display_name,
                        self.commercial_partner_id.olive_lended_organic_case,
                        self.name,
                        self.returned_organic_case))
            lended_case_vals = {
                'partner_id': self.commercial_partner_id.id,
                'regular_qty': self.returned_regular_case * -1,
                'organic_qty': self.returned_organic_case * -1,
                'warehouse_id': wh.id,
                'company_id': self.company_id.id,
                'notes': self.name,
                }
            if self.lended_case_id:
                self.lended_case_id.write(lended_case_vals)
            else:
                lended_case = olco.create(lended_case_vals)
                arrival_vals['lended_case_id'] = lended_case.id
        # Mark palox as returned
        returned_palox.write({
            'borrower_partner_id': False,
            'borrowed_date': False,
            })
        self.write(arrival_vals)
        self.line_ids.write({'state': 'done'})

    def unlink(self):
        for arrival in self:
            if any([l.state == 'done' for l in arrival.line_ids]):
                raise UserError(_(
                    "Cannot delete arrival %s which has some lines in 'Done' state.")
                    % arrival.name)
        return super(OliveArrival, self).unlink()

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(OliveArrival, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        return self.env.user.company_id.current_season_update(res, view_type)


class OliveArrivalLine(models.Model):
    _name = 'olive.arrival.line'
    _description = 'Olive Arrival Line'
    # TODO STRANGE odoo doesn't take _order into account !
    # it seems it is because arrival_id is a M2O...
    _order = 'arrival_id desc, id'

    name = fields.Char(
        string='Arrival Line Number', required=True, readonly=True,
        default='/')
    # The "state" field cannot be a related field because we want to be able to
    # "partially" cancel an arrival
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('cancel', 'Cancel'),
        ], required=True, readonly=True, default='draft', string="State")
    arrival_id = fields.Many2one(
        'olive.arrival', string='Arrival', ondelete='cascade',
        states={'done': [('readonly', True)]})
    # START RELATED fields for arrival
    company_id = fields.Many2one(
        related='arrival_id.company_id', store=True, readonly=True)
    arrival_state = fields.Selection(
        related='arrival_id.state', string='Arrival State',
        readonly=True, store=True)
    arrival_date = fields.Date(
        related='arrival_id.date', readonly=True, store=True)
    season_id = fields.Many2one(
        related='arrival_id.season_id', readonly=True, store=True, index=True)
    warehouse_id = fields.Many2one(
        related='arrival_id.warehouse_id', readonly=True, store=True, index=True)
    commercial_partner_id = fields.Many2one(
        related='arrival_id.partner_id.commercial_partner_id',
        string='Olive Farmer', readonly=True, store=True, index=True)
    partner_olive_culture_type = fields.Selection(
        related='arrival_id.partner_id.commercial_partner_id.olive_culture_type',
        readonly=True, store=True)
    # END RELATED fields for arrival
    leaf_removal = fields.Boolean(
        string='Leaf Removal', states={'done': [('readonly', True)]})
    variant_id = fields.Many2one(
        'olive.variant', string='Olive Variant', required=True,
        states={'done': [('readonly', True)]})
    olive_qty = fields.Float(
        string='Olive Qty (kg)', required=True,
        digits=dp.get_precision('Olive Weight'),
        states={'done': [('readonly', True)]},
        help="Olive quantity in kg."
        "\nFirst-of-day compensation: not included."
        "\nLast-of-day compensation: not deducted.")
    ochard_id = fields.Many2one(
        'olive.ochard', string='Ochard', required=True,
        states={'done': [('readonly', True)]})
    palox_id = fields.Many2one(
        'olive.palox', string='Palox', required=True,
        states={'done': [('readonly', True)]})
    oil_destination = fields.Selection([
        ('withdrawal', 'Withdrawal'),
        ('sale', 'Sale'),
        ('mix', 'Mix'),
        ], string='Oil Destination', required=True,
        states={'done': [('readonly', True)]})
    mix_withdrawal_oil_qty = fields.Float(
        string='Requested Withdrawal Qty (L)',
        digits=dp.get_precision('Olive Oil Volume'),
        states={'done': [('readonly', True)]},
        help="Quantity of olive oil withdrawn by the farmer in liters")
    ripeness = fields.Selection([  # maturité
        ('green', 'Green'),
        ('in_between', 'In Between'),  # Tournantes
        ('optimal', 'Optimal'),
        ('overripen', 'Over Ripen'),  # surmatures
        ], string='Ripeness', required=True,
        states={'done': [('readonly', True)]})
    sanitary_state = fields.Selection([
        ('good', 'Good'),
        ('average', 'Average'),
        ('fair', 'Fair'),  # Passable
        ], string='Sanitary State', required=True,
        states={'done': [('readonly', True)]})
    oil_product_id = fields.Many2one(
        'product.product', string='Oil Type', required=True, index=True,
        domain=[('olive_type', '=', 'oil')],
        states={'done': [('readonly', True)]})
    product_olive_culture_type = fields.Selection(
        related='oil_product_id.olive_culture_type', readonly=True, store=True)
    production_id = fields.Many2one(
        'olive.oil.production', string='Production', readonly=True)
    # START related fields for production
    production_date = fields.Date(
        related='production_id.date', string='Production Date', readonly=True,
        store=True)
    production_state = fields.Selection(
        related='production_id.state', string='Production State',
        readonly=True, store=True)
    compensation_type = fields.Selection(
        related='production_id.compensation_type', readonly=True, store=True)
    # END related fields for production
    oil_ratio = fields.Float(
        string='Oil Gross Ratio (% L)', digits=dp.get_precision('Olive Oil Ratio'),
        readonly=True)
    oil_ratio_net = fields.Float(
        string='Oil Net Ratio (% L)', digits=dp.get_precision('Olive Oil Ratio'),
        readonly=True)
    extra_ids = fields.One2many(
        'olive.arrival.line.extra', 'line_id', string="Extra Items")
    extra_count = fields.Integer(
        compute='_compute_extra_count', string='Extra Item Lines', readonly=True)

    oil_qty_kg = fields.Float(
        string='Oil Qty (kg)',
        readonly=True, digits=dp.get_precision('Olive Oil Volume'),
        help="Oil quantity in kg."
        "\nFirst-of-day compensation: not included."
        "\nLast-of-day compensation: already deducted."
        "\nShrinkage: not deducted."
        "\nFilter loss: not deducted.")
    oil_qty = fields.Float(
        string='Oil Qty (L)',
        readonly=True, digits=dp.get_precision('Olive Oil Volume'),
        help="Oil quantity in liters."
        "\nFirst-of-day compensation: not included."
        "\nLast-of-day compensation: already deducted."
        "\nShrinkage: not deducted."
        "\nFilter loss: not deducted.")
    # We don't have the field 'compensation_last_olive_qty'
    # because it would add un-needed complexity to have it on lines (it would also
    # required to have the compensation ratio on lines, etc...)
    # Instead, we use compensation_oil_qty (value set both for first and last)
    # The sign is always positive, even for last-of-day compensation
    compensation_oil_qty = fields.Float(
        string='Compensation Oil Qty (L)',
        readonly=True, digits=dp.get_precision('Olive Oil Volume'),
        help="This field is used both for last of the day and first of "
        "the day compensations. The quantity is always positive, "
        "even for last-of-day compensations.")
    oil_qty_with_compensation = fields.Float(
        compute='_compute_oil_qty_with_compensation',
        string='Oil Qty with Compensation (L)', store=True,
        readonly=True, digits=dp.get_precision('Olive Oil Volume'),
        help="Oil quantity with compensation in liters."
        "\nFirst-of-day compensation: included."
        "\nLast-of-day compensation: already deducted."
        "\nShrinkage: not deducted."
        "\nFilter loss: not deducted.")

    shrinkage_oil_qty = fields.Float(  # Sale and withdrawal
        string='Shrinkage Oil Qty (L)',
        readonly=True, digits=dp.get_precision('Olive Oil Volume'))
    shrinkage_oil_qty_kg = fields.Float(  # Withdrawal only
        string='Shrinkage Oil Qty (kg)',
        readonly=True, digits=dp.get_precision('Olive Weight'))

    withdrawal_oil_qty_kg = fields.Float(
        string='Withdrawal Oil Qty (kg)',
        readonly=True, digits=dp.get_precision('Olive Weight'),
        help="Withdrawal oil quantity in kg."
        "\nFirst-of-day compensation: not included."
        "\nLast-of-day compensation: already deducted."
        "\nShrinkage: already deducted."
        "\nFilter loss: not applicable.")
    withdrawal_oil_qty = fields.Float(
        string='Withdrawal Oil Qty (L)',
        readonly=True, digits=dp.get_precision('Olive Oil Volume'),
        help="Withdrawal oil quantity in liters."
        "\nFirst-of-day compensation: not included."
        "\nLast-of-day compensation: already deducted."
        "\nShrinkage: already deducted."
        "\nFilter loss: not applicable.")

    to_sale_tank_oil_qty = fields.Float(
        string='Oil Qty to Sale Tank (L)',
        readonly=True, digits=dp.get_precision('Olive Oil Volume'),
        help="Oil sent to sale tank in liters."
        "\nFirst-of-day compensation: not included."
        "\nLast-of-day compensation: already deducted."
        "\nShrinkage: not deducted (because we take shrinkage in sale tank)."
        "\nFilter loss: already deducted.")
    sale_oil_qty = fields.Float(
        string='Oil Qty Sold (L)',
        readonly=True, digits=dp.get_precision('Olive Oil Volume'),
        help="Oil quantity sold in liters."
        "\nFirst-of-day compensation: included."
        "\nLast-of-day compensation: already deducted."
        "\nShrinkage: already deducted."
        "\nFilter loss: already deducted.")
    oil_qty_net = fields.Float(
        string='Net Oil Qty (L)',
        readonly=True, digits=dp.get_precision('Olive Oil Volume'),
        help="Net oil quantity produced in liters."
        "\nFirst-of-day compensation: included."
        "\nLast-of-day compensation: already deducted."
        "\nShrinkage: already deducted."
        "\nFilter loss: already deducted.")

    filter_loss_oil_qty = fields.Float(
        string='Oil Qty Lost in Filter (L)',
        readonly=True, digits=dp.get_precision('Olive Oil Volume'))
    withdrawal_move_id = fields.Many2one(
        'stock.move', string='Withdrawal Move', readonly=True)
    out_invoice_id = fields.Many2one(
        'account.invoice', string="Customer Invoice", readonly=True)
    in_invoice_line_id = fields.Many2one(
        'account.invoice.line', string='Vendor Bill Line', readonly=True)
    in_invoice_id = fields.Many2one(  # TEMPO RESTORE FOR MIG SCRIPT
        'account.invoice', string="Vendor Bill", readonly=True)
    company_currency_id = fields.Many2one(
        related='arrival_id.company_id.currency_id', store=True, readonly=True)
    oil_sale_price_unit = fields.Monetary(
        string='Oil Sale Unit Price',
        readonly=True, currency_field='company_currency_id',
        help="Oil sale price per liter without taxes in company currency.")
    oil_service_sale_price_unit = fields.Monetary(
        string='Oil Service Unit Price (Sale Only)',
        readonly=True, currency_field='company_currency_id',
        help='TODO')
    oil_sale_price_total = fields.Monetary(
        string='Oil Sale Price Total',
        readonly=True, store=True, currency_field='company_currency_id')
    oil_service_sale_price_total = fields.Monetary(
        string='Oil Service Price Total (Sale Only)',
        readonly=True, store=True, currency_field='company_currency_id')

    _sql_constraints = [(
        'olive_qty_positive',
        'CHECK(olive_qty >= 0)',
        'The olive quantity must be positive or null.'), (
        'mix_withdrawal_oil_qty_qty_positive',
        'CHECK(mix_withdrawal_oil_qty >= 0)',
        'The requested withdrawal qty must be positive or null.'),
        ]

    @api.depends('extra_ids')
    def _compute_extra_count(self):
        res = self.env['olive.arrival.line.extra'].read_group(
            [('line_id', 'in', self.ids)], ['line_id'], ['line_id'])
        for re in res:
            self.browse(re['line_id'][0]).extra_count = re['line_id_count']

    @api.depends('oil_qty', 'compensation_type', 'compensation_oil_qty')
    def _compute_oil_qty_with_compensation(self):
        for line in self:
            oil_qty_with_compensation = line.oil_qty
            if line.compensation_type == 'first':
                oil_qty_with_compensation += line.compensation_oil_qty
            line.oil_qty_with_compensation = oil_qty_with_compensation

    @api.depends('sale_oil_qty', 'oil_service_sale_price_unit', 'oil_sale_price_unit')
    def _compute_oil_price_total(self):
        for line in self:
            qty = line.sale_oil_qty
            line.oil_sale_price_total = line.oil_sale_price_unit * qty
            line.oil_service_sale_price_total = line.oil_service_sale_price_unit * qty

    @api.onchange('oil_destination')
    def oil_destination_change(self):
        if self.oil_destination != 'mix':
            self.mix_withdrawal_oil_qty = 0

    def unlink(self):
        for line in self:
            if line.arrival_id:
                raise UserError(_(
                    "Deletion of arrival line %s not allowed because "
                    "it is still linked to arrival %s.") % (
                        line.name, line.arrival_id.name))
        return super(OliveArrivalLine, self).unlink()

    @api.depends('name', 'commercial_partner_id', 'variant_id')
    def name_get(self):
        res = []
        for rec in self:
            name = rec.name
            if rec.commercial_partner_id:
                name = u'%s (%s, %s)' % (name, rec.commercial_partner_id.name, rec.variant_id.name)
            res.append((rec.id, name))
        return res

    def oil_qty_compute_other_vals(self, oil_qty, compensation_oil_qty, ratio):
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
        ctype = self.compensation_type
        if not density:
            raise UserError(_(
                "Missing Olive Oil Density on company '%s'")
                % company.display_name)
        oil_qty = float_round(oil_qty, precision_digits=pr_oil)
        compensation_oil_qty = float_round(
            compensation_oil_qty, precision_digits=pr_oil)
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
            if ctype == 'first':
                sale_oil_qty += compensation_oil_qty
            to_sale_tank_oil_qty = oil_qty - filter_loss_oil_qty

        elif oil_destination == 'mix':
            # When oil_destination == 'mix' and ctype == 'first',
            # the compensation is always for SALE
            # (compensation is withdrawn only when the requested qty is
            # superior to oil production minus shrinkage without compensation
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
                if ctype == 'first':
                    sale_oil_qty += compensation_oil_qty
            else:
                withdrawal_oil_qty = oil_minus_shrinkage
                # rewrite oil destination, for shrinkage stock move
                oil_destination = 'withdrawal'
                # Nothing more to do for ctype == 'first':
            withdrawal_oil_qty_kg = withdrawal_oil_qty * density
        # Compute net ratio, with compensations
        oil_qty_net = oil_minus_shrinkage - filter_loss_oil_qty
        if ctype == 'first':
            oil_qty_net += compensation_oil_qty
        ratio_net = float_round(
            100 * oil_qty_net / self.olive_qty,
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
            'compensation_oil_qty': compensation_oil_qty,
            'oil_qty_net': oil_qty_net,
            }
        return vals

    def pre_prepare_invoice_line(self, product, invoice):
        ailo = self.env['account.invoice.line']
        il_vals = {
            'product_id': product.id,
            'invoice_id': invoice.id,
            }
        il_vals = ailo.play_onchanges(il_vals, ['product_id'])
        if not il_vals.get('account_id'):
            raise UserError(_(
                "Missing account on product '%s' or on it's related product category.")
                % product.display_name)
        return il_vals

    def prepare_invoice(self, invoice_type, invoice_reference=False):
        # pr_tax = self.env['decimal.precision'].precision_get(
        #    'Olive Oil Tax Price Unit')
        # pr_pri = self.env['decimal.precision'].precision_get(
        #    'Product Price')
        aio = self.env['account.invoice']
        partner = self[0].commercial_partner_id
        company = self.env.user.company_id
        origin = [line.name for line in self]
        if len(origin) > 3:
            origin = origin[:3] + ['...']
        origin = ', '.join(origin)
        currency = partner.property_product_pricelist.currency_id
        vals = {
            'partner_id': partner.id,
            'currency_id': currency.id,
            'type': invoice_type,
            'company_id': company.id,
            'origin': origin,
            'reference': invoice_reference,
        }
        vals = aio.play_onchanges(vals, ['partner_id'])
        return vals

    def create_in_invoice_lines(self, invoice):
        ailo = self.env['account.invoice.line'].with_context(type='in_invoice')
        pr_oli = self.env['decimal.precision'].precision_get('Olive Weight')
        partner = invoice.partner_id
        lang = partner.lang or self.env.user.lang
        pricelist = partner.property_product_pricelist
        currency = pricelist.currency_id
        saledict = {}  # key = arrival, value = {'product': sale_oil_qty}
        # I can't do a double groupby via read_group()
        if partner.olive_sale_pricelist_id:
            product2price = partner.olive_sale_pricelist_id.prepare_speeddict()
        else:
            product2price = {}
        for line in self:
            arrival = line.arrival_id
            product = line.oil_product_id
            if float_compare(
                    line.sale_oil_qty, 0, precision_digits=pr_oli) > 0:
                if line.arrival_id in saledict:
                    if product in saledict[arrival]:
                        saledict[arrival][product] += line.sale_oil_qty
                    else:
                        saledict[arrival][product] = line.sale_oil_qty
                else:
                    saledict[arrival] = {product: line.sale_oil_qty}
        total_oil_qty = 0.0
        for arrival, pdict in saledict.items():
            for product, quantity in pdict.items():
                total_oil_qty += quantity
                # TODO: move to prepare line method
                il_vals = self.pre_prepare_invoice_line(product, invoice)
                il_vals['origin'] = arrival.name
                # TODO: translate in right language
                arrival_date_formatted = format_date(
                    fields.Date.from_string(arrival.date),
                    format='short', locale=lang or 'en_US')
                il_vals['name'] = _('%s (Arrival %s dated %s)') % (
                    product.with_context(lang=lang).name,
                    arrival.name, arrival_date_formatted)
                il_vals['quantity'] = quantity
                seller = product._select_seller(
                    partner, quantity=quantity, uom_id=product.uom_id)
                if seller:
                    price_unit = seller.currency_id.compute(
                        seller.price, currency)
                elif product in product2price:
                    price_unit = product2price[product]
                else:
                    price_unit = 0.0
                il_vals['price_unit'] = price_unit
                iline = ailo.create(il_vals)
                arrival.line_ids.write({
                    'in_invoice_line_id': iline.id})
        # TODO translate in right language
        invoice.comment = _(
            "Total oil quantity: %s L") % formatLang(
                self.env, total_oil_qty, dp='Olive Oil Volume')
        invoice.compute_taxes()

    def create_out_invoice_lines(self, invoice):
        ailo = self.env['account.invoice.line'].with_context(type='out_invoice')
        ppo = self.env['product.product']
        pr_oil = self.env['decimal.precision'].precision_get(
            'Olive Oil Volume')
        pr_oli = self.env['decimal.precision'].precision_get('Olive Weight')
        company = invoice.company_id
        partner = invoice.partner_id
        pricelist = partner.property_product_pricelist
        season = self[0].season_id
        totals = self.read_group(
            [('id', 'in', self.ids)],
            ['olive_qty', 'oil_qty', 'oil_qty_with_compensation',
             'shrinkage_oil_qty', 'filter_loss_oil_qty'], [])[0]
        if float_compare(
                totals['oil_qty'], 0, precision_digits=pr_oil) <= 0:
            return False
        if not company.olive_oil_production_product_id:
            raise UserError(_(
                "Missing production product on company %s.")
                % company.name)
        if not company.olive_oil_leaf_removal_product_id:
            raise UserError(_(
                "Missing leaf removal product on company %s.")
                % company.name)
        if not company.olive_oil_tax_product_id:
            raise UserError(_(
                "Missing tax product on company %s.") % company.name)
        if season.early_bird_date and not company.olive_oil_early_bird_discount_product_id:
            raise UserError(_(
                "Missing early bird discount product on company %s.")
                % company.name)
        # Production
        il_vals = self.pre_prepare_invoice_line(
            company.olive_oil_production_product_id, invoice)
        il_vals['quantity'] = totals['olive_qty']
        il_vals['price_unit'] = pricelist.get_product_price(
            company.olive_oil_production_product_id,
            totals['olive_qty'], partner)
        ailo.create(il_vals)
        # additionnal service options are only invoiced on withdrawal
        # cf ('oil_destination', '=', 'withdrawal') in domain
        product_totals = self.read_group(
            [('id', 'in', self.ids), ('oil_destination', '=', 'withdrawal')],
            ['olive_qty', 'oil_product_id'], ['oil_product_id'])
        for product_total in product_totals:
            product = ppo.browse(product_total['oil_product_id'][0])
            for srv_product in product.olive_invoice_service_ids:
                il_vals = self.pre_prepare_invoice_line(srv_product, invoice)
                il_vals['quantity'] = product_total['olive_qty']
                il_vals['price_unit'] = pricelist.get_product_price(
                    srv_product, product_total['olive_qty'], partner)
                ailo.create(il_vals)
        # Discount
        if season.early_bird_date:
            total_disc = self.read_group(
                [('id', 'in', self.ids),
                 ('arrival_date', '<=', season.early_bird_date)],
                ['olive_qty'], [])
            if total_disc and total_disc[0]['olive_qty'] and float_compare(
                    total_disc[0]['olive_qty'], 0,
                    precision_digits=pr_oli) > 0:
                il_vals = self.pre_prepare_invoice_line(
                    company.olive_oil_early_bird_discount_product_id, invoice)
                # with Factur-X, we can't have negative prices
                # so I put a negative qty
                qty = total_disc[0]['olive_qty']
                il_vals['quantity'] = qty * -1
                il_vals['price_unit'] = pricelist.get_product_price(
                    company.olive_oil_early_bird_discount_product_id,
                    qty, partner)
                ailo.create(il_vals)
        # leaf removal
        total_leaf = self.read_group(
            [('id', 'in', self.ids), ('leaf_removal', '=', True)],
            ['olive_qty'], [])
        if (
                total_leaf and total_leaf[0]['olive_qty'] and
                float_compare(
                    total_leaf[0]['olive_qty'], 0,
                    precision_digits=pr_oli) > 0):
            il_vals = self.pre_prepare_invoice_line(
                company.olive_oil_leaf_removal_product_id, invoice)
            qty = total_leaf[0]['olive_qty']
            il_vals['quantity'] = qty
            il_vals['price_unit'] = pricelist.get_product_price(
                company.olive_oil_leaf_removal_product_id,
                qty, partner)
            ailo.create(il_vals)
        # AFIDOL Tax
        tax_product = company.olive_oil_tax_product_id
        if tax_product.uom_id != self.env.ref('product.product_uom_kgm'):
            raise UserError(_(
                "The unit of measure of the oil tax product (%s) should be in kg.")
                % tax_product.display_name)
        il_vals = self.pre_prepare_invoice_line(tax_product, invoice)
        qty = totals['oil_qty_with_compensation'] - totals['shrinkage_oil_qty']\
            - totals['filter_loss_oil_qty']
        price_unit_kg = pricelist.get_product_price(
            tax_product, qty, partner)
        qty_kg = float_round(
            qty * company.olive_oil_density, precision_digits=pr_oil)
        il_vals['quantity'] = qty_kg
        il_vals['price_unit'] = price_unit_kg
        il_vals['name'] += _(u" (%s L = %s kg)") % (
            formatLang(self.env, qty, dp='Olive Oil Volume'),
            formatLang(self.env, qty_kg, dp='Olive Oil Volume'))
        ailo.create(il_vals)
        # Extra items
        extra_totals = self.env['olive.arrival.line.extra'].read_group(
            [
                ('line_id', 'in', self.ids),
                '|', ('fillup', '=', False),
                     ('olive_bottle_free_full', '=', False)],
            ['product_id', 'qty'], ['product_id'])
        for extra_total in extra_totals:
            product_id = extra_total['product_id'][0]
            product = ppo.browse(product_id)
            qty = extra_total['qty']
            il_vals = self.pre_prepare_invoice_line(product, invoice)
            il_vals['quantity'] = qty
            il_vals['price_unit'] = pricelist.get_product_price(
                product, qty, partner)
            ailo.create(il_vals)
        invoice.compute_taxes()

    def in_invoice_create(self):
        aio = self.env['account.invoice']
        vals = self.prepare_invoice('in_invoice')
        invoice = aio.with_context(type='in_invoice').create(vals)
        self.create_in_invoice_lines(invoice)
        return invoice

    def out_invoice_create(self):
        aio = self.env['account.invoice']
        vals = self.prepare_invoice('out_invoice')
        invoice = aio.with_context(type='out_invoice').create(vals)
        self.create_out_invoice_lines(invoice)
        self.write({'out_invoice_id': invoice.id})
        return invoice

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(OliveArrivalLine, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        return self.env.user.company_id.current_season_update(res, view_type)


class OliveArrivalLineExtra(models.Model):
    _name = 'olive.arrival.line.extra'
    _description = 'Extra items linked to the arrival line'

    line_id = fields.Many2one(
        'olive.arrival.line', string='Arrival Line', ondelete='cascade')
    product_id = fields.Many2one(
        'product.product', string='Extra Product',
        required=True, ondelete='restrict',
        domain=[
            ('olive_type', 'in', ('bottle', 'analysis', 'extra_service')),
            '|', ('tracking', '=', False), ('tracking', '=', 'none')])
    product_olive_type = fields.Selection(
        related='product_id.olive_type', readonly=True, store=True)
    qty = fields.Float(
        string='Quantity', default=1,
        digits=dp.get_precision('Product Unit of Measure'), required=True)
    uom_id = fields.Many2one(
        related='product_id.uom_id', readonly=True)
    fillup = fields.Boolean(string='Fill-up')
    olive_bottle_free_full = fields.Boolean(
        related='product_id.olive_bottle_free_full', store=True, readonly=True)

    @api.onchange('product_id')
    def product_id_change(self):
        if (
                self.product_id and
                self.product_id.olive_type == 'bottle' and
                self._context.get('olive_fillup_bottles')):
            self.fillup = True
        else:
            self.fillup = False

    @api.constrains('product_id', 'fillup')
    def line_extra_check(self):
        for extra in self:
            if extra.fillup and extra.product_id.olive_type != 'bottle':
                raise ValidationError(_(
                    "You cannot enable the fill-up option on product '%s' "
                    "which is not an oil bottle.")
                    % extra.product_id.display_name)
