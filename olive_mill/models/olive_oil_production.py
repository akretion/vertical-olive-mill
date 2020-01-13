# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
import odoo.addons.decimal_precision as dp
from odoo.tools import float_compare, float_round


class OliveOilProduction(models.Model):
    _name = 'olive.oil.production'
    _description = 'Olive Oil Production'
    _order = 'date desc, sequence, id desc'
    _inherit = ['mail.thread']

    name = fields.Char(string='Production Number', required=True, default='/')
    company_id = fields.Many2one(
        'res.company', string='Company', ondelete='cascade', required=True,
        states={'done': [('readonly', True)]},
        default=lambda self: self.env['res.company']._company_default_get())
    season_id = fields.Many2one(
        'olive.season', string='Season', required=True, index=True,
        default=lambda self: self.env.user.company_id.current_season_id.id,
        states={'done': [('readonly', True)]})
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse', required=True, index=True,
        domain=[('olive_mill', '=', True)],
        default=lambda self: self.env.user._default_olive_mill_wh(),
        track_visibility='onchange')
    palox_id = fields.Many2one(
        'olive.palox', string='Palox', required=True, readonly=True,
        ondelete='restrict',
        states={'draft': [('readonly', False)]}, track_visibility='onchange')
    # STOCK LOCATIONS
    sale_location_id = fields.Many2one(
        'stock.location', string='Sale Tank',
        states={'done': [('readonly', True)]},
        track_visibility='onchange')
    # not a pb to have withdrawal_location_id required because
    # this field has a default value
    withdrawal_location_id = fields.Many2one(
        'stock.location', string='Withdrawal Location', required=True,
        states={'done': [('readonly', True)]},
        domain=[('olive_tank_type', '=', False), ('usage', '=', 'internal')])
    shrinkage_location_id = fields.Many2one(
        'stock.location', string='Shrinkage Tank',
        states={'done': [('readonly', True)]},
        track_visibility='onchange')
    compensation_location_id = fields.Many2one(
        'stock.location', string='Compensation Tank', readonly=True,
        states={'draft': [('readonly', False)]},  # so that the onchange works
        track_visibility='onchange')
    compensation_sale_location_id = fields.Many2one(
        'stock.location', string='Compensation Sale Tank',
        states={'done': [('readonly', True)]}, track_visibility='onchange')
    compensation_oil_product_id = fields.Many2one(
        'product.product', string='Compensation Oil Type', readonly=True)
    compensation_type = fields.Selection([
        ('none', 'No Compensation'),
        ('first', 'First of the Day'),
        ('last', 'Last of the Day'),
        ], string='Compensation Type', default='none', readonly=True,
        track_visibility='onchange')
    compensation_last_olive_qty = fields.Float(
        string='Olive Compensation Qty',
        digits=dp.get_precision('Olive Weight'), readonly=True,
        track_visibility='onchange', help="Olive compensation in kg")
    compensation_ratio = fields.Float(
        string='Compensation Ratio', digits=dp.get_precision('Olive Oil Ratio'),
        readonly=True, track_visibility='onchange')
    olive_qty = fields.Float(
        string='Olive Qty', compute='_compute_lines',
        digits=dp.get_precision('Olive Weight'), readonly=True, store=True,
        track_visibility='onchange',
        help='Olive quantity without compensation in kg')
    to_sale_tank_oil_qty = fields.Float(
        string='Oil Qty to Sale Tank (L)', compute='_compute_lines',
        digits=dp.get_precision('Olive Oil Volume'), readonly=True, store=True)
    to_compensation_sale_tank_oil_qty = fields.Float(
        string='Oil Qty to Compensation Sale Tank (L)', compute='_compute_lines',
        digits=dp.get_precision('Olive Oil Volume'), readonly=True, store=True)
    compensation_oil_qty = fields.Float(
        string='Oil Compensation (L)',
        digits=dp.get_precision('Olive Oil Volume'), readonly=True,
        track_visibility='onchange')
    compensation_oil_qty_kg = fields.Float(
        string='Oil Compensation (kg)',
        digits=dp.get_precision('Olive Weight'), readonly=True)
    oil_destination = fields.Selection([
        ('withdrawal', 'Withdrawal'),
        ('sale', 'Sale'),
        ('mix', 'Mix'),
        ], string='Oil Destination', compute='_compute_oil_destination',
        readonly=True)
    oil_product_id = fields.Many2one(
        'product.product', string='Oil Type', readonly=True,
        track_visibility='onchange')
    olive_culture_type = fields.Selection(
        related='oil_product_id.olive_culture_type', readonly=True, store=True)
    olive_culture_type_logo = fields.Binary(
        compute='_compute_olive_culture_type_logo',
        string='Olive Culture Type Logo', readonly=True)
    oil_qty_kg = fields.Float(
        string='Oil Quantity (kg)', digits=dp.get_precision('Olive Weight'),
        readonly=True, track_visibility='onchange')  # written by ratio2force wizard
    oil_qty = fields.Float(
        string='Oil Quantity (L)', digits=dp.get_precision('Olive Oil Volume'),
        readonly=True, track_visibility='onchange')  # written by ratio2force wizard
    ratio = fields.Float(
        string='Gross Ratio (% L)', digits=dp.get_precision('Olive Oil Ratio'),
        readonly=True, group_operator='avg',
        help="This ratio gives the number of liters of olive oil for "
        "100 kg of olives.")  # Yes, it's a ratio between liters and kg !!!
    date = fields.Date(
        string='Date', default=fields.Date.context_today, required=True,
        states={'done': [('readonly', True)]}, track_visibility='onchange')
    day_position = fields.Integer(
        compute='_compute_day_position', readonly=True, string='Order')
    sample = fields.Boolean(
        string='Sample', readonly=True,
        states={'draft': [('readonly', False)], 'ratio': [('readonly', False)]})
    farmers = fields.Char(string='Farmers', readonly=True)
    decanter_speed = fields.Integer(
        string='Decanter Speed', states={'done': [('readonly', True)]})
    sequence = fields.Integer(default=10)
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
    sale_move_id = fields.Many2one(
        'stock.move', string='Sale Move', readonly=True)
    compensation_last_move_id = fields.Many2one(
        'stock.move', string='Compensation Last of the Day Move', readonly=True)
    line_ids = fields.One2many(
        'olive.arrival.line', 'production_id', string='Arrival Lines',
        readonly=True)

    _sql_constraints = [
        ('oil_qty_kg_positive', 'CHECK(oil_qty_kg >= 0)', 'The oil quantity must be positive.'),
        ('compensation_last_olive_qty_positive', 'CHECK(compensation_last_olive_qty >= 0)', 'The compensation olive quantity must be positive.'),
        ('compensation_oil_qty_positive', 'CHECK(compensation_oil_qty >= 0)', 'The compensation oil quantity must be positive.'),
        ]

    @api.constrains('compensation_ratio', 'compensation_type')
    def check_production(self):
        for prod in self:
            min_ratio, max_ratio = prod.company_id.olive_min_max_ratio()
            if prod.compensation_type == 'last':
                cratio = prod.compensation_ratio
                if cratio < min_ratio or cratio > max_ratio:
                    raise ValidationError(_(
                        "The compensation ratio (%s %%) is not realistic.")
                        % cratio)

    @api.onchange('warehouse_id')
    def warehouse_change(self):
        if self.warehouse_id:
            wh = self.warehouse_id
            if wh.olive_withdrawal_loc_id:
                self.withdrawal_location_id = wh.olive_withdrawal_loc_id
            if wh.olive_compensation_loc_id:
                self.compensation_location_id = wh.olive_compensation_loc_id

    @api.onchange('palox_id')
    def palox_change(self):
        if self.palox_id:
            self.oil_product_id = self.palox_id.oil_product_id
        else:
            self.oil_product_id = False

    @api.depends(
        'line_ids.olive_qty', 'line_ids.to_sale_tank_oil_qty',
        'line_ids.oil_destination', 'line_ids.compensation_oil_qty')
    def _compute_lines(self):
        res = self.env['olive.arrival.line'].read_group(
            [('production_id', 'in', self.ids)],
            ['production_id', 'olive_qty', 'to_sale_tank_oil_qty'],
            ['production_id'])
        for re in res:
            production = self.browse(re['production_id'][0])
            production.olive_qty = re['olive_qty']
            production.to_sale_tank_oil_qty = re['to_sale_tank_oil_qty']
        cres = self.env['olive.arrival.line'].read_group(
            [('production_id', 'in', self.ids),
             ('oil_destination', 'in', ('sale', 'mix'))],
            ['production_id', 'compensation_oil_qty'],
            ['production_id'])
        for cre in cres:
            production = self.browse(cre['production_id'][0])
            production.to_compensation_sale_tank_oil_qty = cre['compensation_oil_qty']

    @api.depends('line_ids.oil_destination')
    def _compute_oil_destination(self):
        for prod in self:
            oil_destination = False
            if prod.line_ids:
                dests = [line.oil_destination for line in prod.line_ids]
                if all([dest == 'sale' for dest in dests]):
                    oil_destination = 'sale'
                elif all([dest == 'withdrawal' for dest in dests]):
                    oil_destination = 'withdrawal'
                else:
                    oil_destination = 'mix'
            prod.oil_destination = oil_destination

    @api.depends('oil_product_id.olive_culture_type')
    def _compute_olive_culture_type_logo(self):
        type2filename = {
            'organic': 'organic_logo_done.png',
            'conversion': 'organic_logo_conversion_done.png',
        }
        for prod in self:
            logo = False
            if prod.olive_culture_type in type2filename:
                filename = type2filename[prod.olive_culture_type]
                fname_path = 'olive_mill/static/image/%s' % filename
                f = tools.file_open(fname_path, 'rb')
                f_binary = f.read()
                if f_binary:
                    logo = f_binary.encode('base64')
            prod.olive_culture_type_logo = logo

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
        self.write({
            'state': 'cancel',
            'oil_qty': 0,
            'oil_qty_kg': 0,
            'ratio': 0,
            'to_sale_tank_oil_qty': 0,
            'to_compensation_sale_tank_oil_qty': 0,
            })

    def back2draft(self):
        self.ensure_one()
        assert self.state == 'cancel'
        self.write({'state': 'draft'})

    def draft2ratio(self):
        """Attach arrival lines to olive.oil.production"""
        self.ensure_one()
        assert self.state == 'draft'
        oalo = self.env['olive.arrival.line']
        pr_oli = self.env['decimal.precision'].precision_get('Olive Weight')
        if not self.line_ids:
            draft_lines = oalo.search([
                ('palox_id', '=', self.palox_id.id),
                ('warehouse_id', '=', self.warehouse_id.id),
                ('state', '=', 'draft'),
                ('production_id', '=', False)])
            if draft_lines:
                raise UserError(_(
                    "Arrival line %s is linked to palox %s but it is still "
                    "in draft state. If you want to take this arrival line "
                    "in this production, you should validate the arrival. "
                    "Otherwise, you should cancel the arrival.")
                    % (draft_lines[0].name, self.palox_id.name))
            done_lines = oalo.search([
                ('palox_id', '=', self.palox_id.id),
                ('warehouse_id', '=', self.warehouse_id.id),
                ('state', '=', 'done'),
                ('production_id', '=', False)])
            if not done_lines:
                raise UserError(_(
                    "The palox %s is empty or currently in production.")
                    % self.palox_id.name)
            done_lines.write({'production_id': self.id})
            # Free the palox
            self.palox_id.oil_product_id = False
        oil_dests = []
        oil_product = False
        sample = False
        farmers = []
        for l in self.line_ids:
            oil_dests.append(l.oil_destination)
            if oil_product:
                if oil_product != l.oil_product_id:
                    raise UserError(_(
                        "The oil type of arrival line %s is %s, "
                        "but it is %s on the first arrival line "
                        "of palox %s.") % (
                            l.name,
                            l.oil_product_id.name,
                            oil_product.name,
                            self.palox_id.name))
            else:
                oil_product = l.oil_product_id
            if l.season_id != self.season_id:
                raise UserError(_(
                    "The season of arrival line %s is '%s', but the oil "
                    "production %s is attached to season '%s'.") % (
                        l.name, l.season_id.name, self.name, self.season_id.name))
            farmers.append(l.commercial_partner_id.name)
            if float_compare(l.olive_qty, 0, precision_digits=pr_oli) <= 0:
                raise UserError(_(
                    "On line %s, the olive quantity is null.") % l.name)
            if not sample:
                for extra in l.extra_ids:
                    if extra.product_olive_type == 'analysis':
                        sample = True
                        break
        sloc = self.warehouse_id.olive_get_shrinkage_tank(oil_product)

        self.write({
            'farmers': u' / '.join(farmers),
            'sample': sample,
            'state': 'ratio',
            'oil_product_id': oil_product.id,
            'shrinkage_location_id': sloc and sloc.id or False
            })

    def start_ratio2force(self):
        self.ensure_one()
        assert self.state == 'ratio'
        cloc = self.compensation_location_id
        # We cannot do that in the wizard olive.oil.production.compensation
        # because, at the time of the wizard, the previous last of day
        # compensation may not be done yet, so the compensation tank
        # may be empty
        if self.compensation_type == 'last':
            # cloc.oil_product_id will be written a second time in
            # check2done (in case the wizard swap product is used)
            cloc.sudo().oil_product_id = self.oil_product_id.id
        compensation_oil_qty = self.compensation_check_tank()
        if self.compensation_type == 'first':
            density = self.company_id.olive_oil_density
            self.write({
                'compensation_oil_qty': compensation_oil_qty,
                'compensation_oil_qty_kg': compensation_oil_qty * density,
                'compensation_oil_product_id': cloc.oil_product_id.id,
                })
        action = self.env['ir.actions.act_window'].for_xml_id(
            'olive_mill', 'olive_oil_production_ratio2force_action')
        action['context'] = {
            'default_production_id': self.id,
            'default_compensation_sale_location_id': self.compensation_sale_location_id.id or False,
            'default_sale_location_id': self.sale_location_id.id or False,
            }
        return action

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
        self.write({'state': new_state})

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
        pr_oil = self.env['decimal.precision'].precision_get('Olive Oil Volume')
        pr_ratio = self.env['decimal.precision'].precision_get('Olive Oil Ratio')
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
            if float_compare(first_line_oil_qty, total_oil_qty, precision_digits=pr_oil) > 0:
                raise UserError(_(
                    "The forced ratio (%s %% on arrival line %s) is not possible because it would "
                    "attribute more oil than the produced oil.") % (
                        first_line_ratio, first_line_to_process.name))
            total_oil_prorata = total_oil_qty - first_line_oil_qty
            total_olive_prorata = self.olive_qty - first_line_to_process.olive_qty
        else:
            first_line_to_process = self.line_ids[0]
            first_line_ratio = self.ratio
            first_line_oil_qty = first_line_to_process.olive_qty * total_oil_qty / self.olive_qty
            total_oil_prorata = total_oil_qty
            total_olive_prorata = self.olive_qty
        # The compensation oil qty is distributed pro-rata of the oil_qty ;
        # so the forced ratio is in-directly taken into account
        first_line_compensation_oil_qty = False
        if total_compensation_oil_qty:
            first_line_compensation_oil_qty = total_compensation_oil_qty * first_line_oil_qty / total_oil_qty
        first_line_vals = first_line_to_process.oil_qty_compute_other_vals(
            first_line_oil_qty, first_line_compensation_oil_qty, first_line_ratio)
        # Write on first line
        first_line_to_process.write(first_line_vals)
        lines = [line for line in self.line_ids if line != first_line_to_process]
        for line in lines:
            # compute oil qty with a pro-rata using special values total_oil_prorata
            # and total_olive_prorata
            oil_qty = line.olive_qty * total_oil_prorata / total_olive_prorata
            compensation_oil_qty = False
            oil_qty_for_ratio = oil_qty
            if total_compensation_oil_qty:
                compensation_oil_qty = total_compensation_oil_qty * oil_qty / total_oil_qty
            if ctype == 'first':
                oil_qty_for_ratio += compensation_oil_qty
            ratio = float_round(
                100 * oil_qty_for_ratio / line.olive_qty, precision_digits=pr_ratio)
            vals = line.oil_qty_compute_other_vals(
                oil_qty, compensation_oil_qty, ratio)
            # Write on other lines
            line.write(vals)

    def compensation_check_tank(self):
        '''Performs check and return the qty of the tank'''
        self.ensure_one()
        ctype = self.compensation_type
        pr_oil = self.env['decimal.precision'].precision_get('Olive Oil Volume')
        cloc = self.compensation_location_id
        if not cloc:
            if ctype == 'none':
                return 0
            raise UserError(_(
                "The production %s uses compensation, so you must set the "
                "compensation tank.") % self.name)
        cloc.olive_oil_tank_check(raise_if_not_merged=False, raise_if_empty=False)
        cqty = cloc.olive_oil_qty
        if ctype in ('last', 'none'):
            # cloc must be empty
            if float_compare(cqty, 0, precision_digits=pr_oil) > 0:
                raise UserError(_(
                    "The production %s uses last of day compensation or no compensation, so the compensation tank must be empty before the operation.") % self.name)
        elif ctype == 'first':
            if float_compare(cqty, 0, precision_digits=pr_oil) <= 0:
                raise UserError(_(
                    "The production %s uses first of day compensation, so the compensation tank mustn't be empty before the operation.") % self.name)
        return cqty

    def check2done(self):
        self.ensure_one()
        assert self.state == 'check'
        splo = self.env['stock.production.lot']
        smo = self.env['stock.move']
        pr_oil = self.env['decimal.precision'].precision_get('Olive Oil Volume')
        wloc = self.warehouse_id.olive_withdrawal_loc_id
        stock_loc = self.warehouse_id.lot_stock_id
        sale_loc = self.sale_location_id
        cloc = self.compensation_location_id
        csale_loc = self.compensation_sale_location_id
        oil_product = self.oil_product_id
        season = self.season_id
        to_shrinkage_tank_oil_qty = 0.0
        ctype = self.compensation_type

        self.compensation_check_tank()
        if ctype == 'last':
            if float_compare(self.compensation_oil_qty, 0, precision_digits=pr_oil) <= 0:
                raise UserError(_(
                    "The production %s uses last of day compensation, so the "
                    "'Oil Compensation' should be positive.") % self.name)
        # create prod lot
        # No expiry date on olive oil in tanks
        prodlot = splo.create({
            'olive_production_id': self.id,
            'product_id': oil_product.id,
            'name': self.name,
            })
        for line in self.line_ids:
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
                    'restrict_partner_id': line.commercial_partner_id.id,
                    })
                wmove.action_done()
                assert wmove.state == 'done'
                line.withdrawal_move_id = wmove.id
            for extra in line.extra_ids:
                if extra.product_id.tracking and extra.product_id.tracking != 'none':
                    raise UserError(_(
                        "Can't select the product '%s' in extra items of "
                        "line %s because it is tracked by lot or serial.")
                        % (extra.product_id.display_name, line.name))
                # Cannot use 'restrict_partner_id'
                # because it would create a negative quant with owner
                # on src location
                extra_move = smo.create({
                    'product_id': extra.product_id.id,
                    'name': _('Olive oil production %s: extra item withdrawal related to arrival line %s') % (self.name, line.name),
                    'location_id': stock_loc.id,
                    'location_dest_id': wloc.id,
                    'product_uom': extra.product_id.uom_id.id,
                    'origin': self.name,
                    'product_uom_qty': extra.qty,
                    })
                extra_move.action_done()
                # set owner on quants
                extra_move.sudo().quant_ids.write(
                    {'owner_id': line.commercial_partner_id.id})
                assert extra_move.state == 'done'
            if line.oil_destination == 'withdrawal':
                to_shrinkage_tank_oil_qty += line.shrinkage_oil_qty
        prod_vals = {
            'state': 'done',
            'done_datetime': fields.Datetime.now(),
            }
        # Move to sale tank
        if float_compare(self.to_sale_tank_oil_qty, 0, precision_digits=pr_oil) > 0:
            if not sale_loc:
                raise UserError(_(
                    "Sale tank is not set on oil production %s.") % self.name)
            sale_loc.olive_oil_tank_check(
                raise_if_not_merged=False, raise_if_empty=False)
            sale_loc.olive_oil_tank_compatibility_check(oil_product, season)
            sale_move = smo.create({
                'product_id': oil_product.id,
                'name': _('Olive oil production %s to sale tank') % self.name,
                'location_id': oil_product.property_stock_production.id,
                'location_dest_id': sale_loc.id,
                'product_uom': oil_product.uom_id.id,
                'origin': self.name,
                'product_uom_qty': self.to_sale_tank_oil_qty,
                'restrict_lot_id': prodlot.id,
                })
            sale_move.action_done()
            assert sale_move.state == 'done'
            prod_vals['sale_move_id'] = sale_move.id

        # Compensation LAST move
        if (
                ctype == 'last' and
                float_compare(self.compensation_oil_qty, 0, precision_digits=pr_oil) > 0):
            cmove = smo.create({
                'product_id': oil_product.id,
                'name': _('Olive oil production %s to compensation tank') % self.name,
                'location_id': oil_product.property_stock_production.id,
                'location_dest_id': cloc.id,
                'product_uom': oil_product.uom_id.id,
                'origin': self.name,
                'product_uom_qty': self.compensation_oil_qty,
                'restrict_lot_id': prodlot.id,
                })
            cmove.action_done()
            assert cmove.state == 'done'
            prod_vals['compensation_last_move_id'] = cmove.id
            cloc.sudo().oil_product_id = oil_product.id

        # Shrinkage move
        if float_compare(to_shrinkage_tank_oil_qty, 0, precision_digits=pr_oil) > 0:
            shrinkage_loc = self.shrinkage_location_id
            if not shrinkage_loc:
                raise UserError(_(
                    "Shrinkage tank is not set on oil production %s.") % self.name)
            # We don't use the oil_product for shrinkage, because we would
            # have several different oil products in the shrinkage tank
            # We use shrinkage_product instead
            shrinkage_product = shrinkage_loc.oil_product_id
            if not shrinkage_product:
                raise UserError(_(
                    "Missing oil product on shrinkage tank %s.")
                    % shrinkage_loc.display_name)
            if not shrinkage_product.shrinkage_prodlot_id:
                raise UserError(_(
                    "Missing shrinkage production lot on product '%s'.")
                    % shrinkage_product.display_name)
            shrinkage_move = smo.create({
                'product_id': shrinkage_product.id,
                'name': _('Olive Oil Production %s: Shrinkage') % self.name,
                'location_id': shrinkage_product.property_stock_production.id,
                'location_dest_id': shrinkage_loc.id,
                'product_uom': shrinkage_product.uom_id.id,
                'origin': self.name,
                'product_uom_qty': to_shrinkage_tank_oil_qty,
                'restrict_lot_id': shrinkage_product.shrinkage_prodlot_id.id,
                })
            shrinkage_move.action_done()
            prod_vals['shrinkage_move_id'] = shrinkage_move.id
        action = {}
        # Distribute compensation
        if ctype == 'first':
            # In sale and mix, the compensation is always sold
            if all([line.oil_destination in ('sale', 'mix') for line in self.line_ids]):
                # full trf
                if not csale_loc:
                    raise UserError(_(
                        "On oil production %s which has first-of-day "
                        "compensation, you must set a compensation sale tank.") % self.name)
                cloc.olive_oil_transfer(
                    csale_loc, 'full', self.warehouse_id,
                    origin=_('Empty compensation tank to sale tank'), auto_validate=True)
            else:
                # partial trf
                if float_compare(self.to_compensation_sale_tank_oil_qty, 0, precision_digits=pr_oil) > 0:
                    if not csale_loc:
                        raise UserError(_(
                            "On oil production %s which has first-of-day "
                            "compensation, you must set a compensation sale tank.") % self.name)
                    cloc.olive_oil_transfer(
                        csale_loc, 'partial', self.warehouse_id,
                        partial_transfer_qty=self.to_compensation_sale_tank_oil_qty,
                        origin=_('Partial transfer of compensation tank to sale tank'),
                        auto_validate=True)
                wlines = [l for l in self.line_ids if l.oil_destination == 'withdrawal']
                origin = _('Transfer of compensation tank to withdrawal location')
                while wlines:
                    # work on 1st line of wlines
                    if len(wlines) == 1:
                        # full trf for the last withdrawal line
                        cloc.olive_oil_transfer(
                            wloc, 'full', self.warehouse_id,
                            dest_partner=wlines[0].commercial_partner_id,
                            origin=origin, auto_validate=True)
                    else:
                        cloc.olive_oil_transfer(
                            wloc, 'partial', self.warehouse_id,
                            dest_partner=wlines[0].commercial_partner_id,
                            partial_transfer_qty=wlines[0].compensation_oil_qty,
                            origin=origin, auto_validate=True)

                    # remove first line of wlines
                    wlines.pop(0)
            # DON'T remove oil_product_id on compensation tank
            # because we now go through olive_tank_type_change()
            # even when compensation = 'none', so the product must always be set
            # cloc.sudo().oil_product_id = False
        # If last = sale and first next day = sale, copy sale tank of last to
        # compensation sale tank of first
        # if last = withdrawal and first = sale, open wizard to select sale tank
        elif ctype == 'last':
            # try to find first of day compensation in the future
            next_first_prod = self.search([
                ('warehouse_id', '=', self.warehouse_id.id),
                ('season_id', '=', self.season_id.id),
                ('compensation_location_id', '=', self.compensation_location_id.id),
                ('state', '=', 'ratio'),
                ('date', '>', self.date),
                ('compensation_type', '=', 'first'),
                ], order='date', limit=1)
            if next_first_prod:
                if self.oil_destination in ('sale', 'mix') and next_first_prod.oil_destination in ('sale', 'mix'):
                    # simple copy
                    next_first_prod.compensation_sale_location_id = self.sale_location_id.id
                    next_first_prod.message_post(_(
                        "Compensation sale tank automatically set upon "
                        "closing of last-of-day production "
                        "<a href=# data-oe-model=olive.oil.production data-oe-id=%d>%s</a>.") % (self.id, self.name))
                elif self.oil_destination == 'withdrawal' and next_first_prod.oil_destination in ('sale', 'mix'):
                    # start wizard
                    action = self.env.ref('olive_mill.olive_oil_production_done_last_action').read()[0]
                    action['context'] = {
                        'default_last_production_id': self.id,
                        'default_next_first_production_id': next_first_prod.id,
                        }

        self.write(prod_vals)
        self.update_arrival_production_done()
        return action

    def update_arrival_production_done(self):
        self.ensure_one()
        oalo = self.env['olive.arrival.line']
        oao = self.env['olive.arrival']
        arrivals = oao
        for line in self.line_ids:
            arrivals |= line.arrival_id
        assert arrivals
        arrivals_res = oalo.read_group(
            [('production_state', '=', 'done'), ('arrival_id', 'in', arrivals.ids)],
            ['oil_qty_net', 'olive_qty', 'arrival_id'],
            ['arrival_id'])
        for arrival_re in arrivals_res:
            arrival = oao.browse(arrival_re['arrival_id'][0])
            olive_qty_pressed = arrival_re['olive_qty']
            oil_qty_net = arrival_re['oil_qty_net']
            oil_ratio_net = olive_ratio_net = 0.0
            if olive_qty_pressed:
                oil_ratio_net = 100 * oil_qty_net / olive_qty_pressed
            if oil_qty_net:
                olive_ratio_net = olive_qty_pressed / oil_qty_net
            arrival.write({
                'olive_qty_pressed': olive_qty_pressed,
                'oil_qty_net': oil_qty_net,
                'oil_ratio_net': oil_ratio_net,
                'olive_ratio_net': olive_ratio_net,
                })

    def unlink(self):
        for production in self:
            if production.state == 'done':
                raise UserError(_(
                    "Cannot delete production %s which is in Done state.")
                    % production.name)
        return super(OliveOilProduction, self).unlink()

    def detach_lines(self):
        self.ensure_one()
        self.line_ids.write({'production_id': False})
        self.palox_id.oil_product_id = self.oil_product_id.id

    def _compute_day_position(self):
        for prod in self:
            if prod.state == 'cancel':
                day_position = 0
            else:
                # same order as on-screen
                same_day_prod = self.search(
                    [('date', '=', prod.date), ('state', '!=', 'cancel')])
                same_day_reverse_order = [p for p in same_day_prod]
                same_day_reverse_order.reverse()
                index = same_day_reverse_order.index(prod)
                day_position = index + 1
            prod.day_position = day_position

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(OliveOilProduction, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        return self.env.user.company_id.current_season_update(res, view_type)
