# Copyright 2018-2023 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, tools, Command, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round


class OliveOilProduction(models.Model):
    _name = 'olive.oil.production'
    _description = 'Olive Oil Production'
    _order = 'date desc, sequence, id desc'
    _check_company_auto = True
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Production Number', required=True, default=lambda self: _('New'))
    company_id = fields.Many2one(
        'res.company', string='Company', ondelete='cascade', required=True,
        default=lambda self: self.env.company)
    season_id = fields.Many2one(
        'olive.season', string='Season', required=True, index=True,
        default=lambda self: self.env.company.current_season_id.id,
        domain="[('company_id', '=', company_id)]", check_company=True)
    current_season = fields.Boolean(
        compute='_compute_current_season', search='_search_current_season')
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse', required=True, index=True,
        domain="[('olive_mill', '=', True), ('company_id', '=', company_id)]",
        default=lambda self: self.env.user._default_olive_mill_wh(),
        check_company=True, tracking=True)
    palox_ids = fields.Many2many(
        'olive.palox', string='Paloxes', required=True,
        ondelete='restrict', check_company=True, tracking=True)
    palox_ids_str = fields.Char(compute='_compute_palox_ids_str', store=True)
    # STOCK LOCATIONS
    sale_location_id = fields.Many2one(
        'stock.location', string='Sale Tank', check_company=True,
        domain="[('olive_tank_type', '=', 'regular'), ('oil_product_id', '=', oil_product_id), ('olive_season_id', '=', season_id), ('company_id', '=', company_id)]",
        tracking=True)
    # We would like to have withdrawal_location_id required, but it blocks the
    # wizard olive.palox.generate.production
    withdrawal_location_id = fields.Many2one(
        'stock.location', compute="_compute_locations", store=True, readonly=False,
        string='Withdrawal Location', required=False, check_company=True,
        domain="[('olive_tank_type', '=', False), ('usage', '=', 'internal'), ('company_id', '=', company_id)]")
    shrinkage_location_id = fields.Many2one(
        'stock.location', string='Shrinkage Tank',
        domain="[('olive_tank_type', '=', 'shrinkage'), ('olive_season_id', '=', season_id), ('company_id', '=', company_id)]",
        check_company=True, tracking=True)
    olive_qty = fields.Float(
        string='Olive Qty', compute='_compute_lines',
        digits='Olive Weight', store=True, tracking=True,
        help='Olive quantity in kg')
    to_sale_tank_oil_qty = fields.Float(
        string='Oil Qty to Sale Tank (L)', compute='_compute_lines',
        digits='Olive Oil Volume', store=True)
    oil_destination = fields.Selection([
        ('withdrawal', 'Withdrawal'),
        ('sale', 'Sale'),
        ('mix', 'Mix'),
        ], string='Oil Destination', compute='_compute_oil_destination')
    oil_product_id = fields.Many2one(
        'product.product', compute="_compute_oil_product_id", store=True,
        string='Oil Type', tracking=True)
    olive_culture_type = fields.Selection(
        related='oil_product_id.olive_culture_type', store=True)
    olive_culture_type_logo = fields.Binary(
        compute='_compute_olive_culture_type_logo',
        string='Olive Culture Type Logo')
    oil_qty_kg = fields.Float(
        string='Oil Quantity (kg)', digits='Olive Weight',
        readonly=True, tracking=True)  # written by ratio2force wizard
    oil_qty = fields.Float(
        string='Oil Quantity (L)', digits='Olive Oil Volume',
        readonly=True, tracking=True)  # written by ratio2force wizard
    ratio = fields.Float(
        string='Gross Ratio (% L)', digits='Olive Oil Ratio',
        readonly=True, aggregator='avg',
        help="This ratio gives the number of liters of olive oil for "
        "100 kg of olives.")  # Yes, it's a ratio between liters and kg !!!
    date = fields.Date(
        string='Date', default=fields.Date.context_today, required=True, tracking=True)
    day_position = fields.Integer(
        compute='_compute_day_position', string='Order')
    sample = fields.Boolean()
    farmers = fields.Char(readonly=True)
    decanter_speed = fields.Integer()
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
        tracking=True)
    done_datetime = fields.Datetime(
        string='Date Done', readonly=True, copy=False)
    shrinkage_move_id = fields.Many2one(
        'stock.move', string='Shrinkage Stock Move', readonly=True, copy=False)
    sale_move_id = fields.Many2one(
        'stock.move', string='Sale Move', readonly=True)
    line_ids = fields.One2many(
        'olive.arrival.line', 'production_id', string='Arrival Lines',
        readonly=True)

    _sql_constraints = [
        ('oil_qty_kg_positive', 'CHECK(oil_qty_kg >= 0)', 'The oil quantity must be positive.'),
        ]

    @api.depends('palox_ids')
    def _compute_palox_ids_str(self):
        for prod in self:
            palox_ids_str = False
            if prod.palox_ids:
                palox_ids_str = ', '.join([x.name for x in prod.palox_ids])
            prod.palox_ids_str = palox_ids_str

    @api.depends('warehouse_id')
    def _compute_locations(self):
        for prod in self:
            if prod.warehouse_id:
                wh = prod.warehouse_id
                if wh.olive_withdrawal_loc_id:
                    prod.withdrawal_location_id = wh.olive_withdrawal_loc_id

    @api.depends('palox_ids')
    def _compute_oil_product_id(self):
        for prod in self:
            oil_product_id = False
            if prod.palox_ids:
                oil_product_id = prod.palox_ids[0].oil_product_id
            prod.oil_product_id = oil_product_id

    @api.depends(
        'line_ids.olive_qty', 'line_ids.to_sale_tank_oil_qty',
        'line_ids.oil_destination')
    def _compute_lines(self):
        res = self.env['olive.arrival.line']._read_group(
            [('production_id', 'in', self.ids)],
            groupby=['production_id'],
            aggregates=['olive_qty:sum', 'to_sale_tank_oil_qty:sum'])
        for production, olive_qty, to_sale_tank_oil_qty in res:
            production.olive_qty = olive_qty
            production.to_sale_tank_oil_qty = to_sale_tank_oil_qty

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

    def _compute_current_season(self):
        for prod in self:
            if prod.company_id.current_season_id == prod.season_id:
                prod.current_season = True
            else:
                prod.current_season = False

    def _search_current_season(self, operator, value):
        return self.env['res.company']._search_current_season(operator, value)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'company_id' in vals:
                self = self.with_company(vals['company_id'])
            if vals.get('name', _("New")) == _("New"):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'olive.oil.production') or _('New')
        return super().create(vals_list)

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
            draft_line = oalo.search([
                ('palox_id', 'in', self.palox_ids.ids),
                ('warehouse_id', '=', self.warehouse_id.id),
                ('state', '=', 'draft'),
                ('production_id', '=', False)], limit=1)
            if draft_line:
                raise UserError(_(
                    "Arrival line %s is linked to palox %s but it is still "
                    "in draft state. If you want to take this arrival line "
                    "in this production, you should validate the arrival. "
                    "Otherwise, you should cancel the arrival.")
                    % (draft_line.name, draft_line.palox_id.name))
            lines_to_attach = oalo
            for palox in self.palox_ids:
                done_lines = oalo.search([
                    ('palox_id', '=', palox.id),
                    ('warehouse_id', '=', self.warehouse_id.id),
                    ('state', '=', 'done'),
                    ('production_id', '=', False)])
                if not done_lines:
                    raise UserError(_(
                        "The palox %s is empty or currently in production.")
                        % palox.name)
                lines_to_attach |= done_lines
            lines_to_attach.write({'production_id': self.id})
            # Free the palox
            self.palox_ids.write({'oil_product_id': False})
        oil_dests = []
        oil_product = False
        first_arrival_line = self.line_ids[0]
        oil_product = first_arrival_line.oil_product_id
        sample = False
        farmers = []
        for line in self.line_ids:
            oil_dests.append(line.oil_destination)
            if line.oil_product_id != oil_product:
                raise UserError(_(
                    "The oil type of arrival line %s is %s, "
                    "but it is %s on the first arrival line %s. All the "
                    "arrival lines must have the same oil type.") % (
                        line.name,
                        line.oil_product_id.name,
                        oil_product.name,
                        first_arrival_line.name))
            if line.season_id != self.season_id:
                raise UserError(_(
                    "The season of arrival line %s is '%s', but the oil "
                    "production %s is attached to season '%s'.") % (
                        line.name, line.season_id.name, self.name, self.season_id.name))
            farmers.append(line.commercial_partner_id.name)
            if float_compare(line.olive_qty, 0, precision_digits=pr_oli) <= 0:
                raise UserError(_(
                    "On line %s, the olive quantity is null.") % line.name)
            if not sample:
                for extra in line.extra_ids:
                    if extra.product_detailed_type == 'olive_analysis':
                        sample = True
                        break
        sloc = self.warehouse_id.olive_get_shrinkage_tank(oil_product)

        self.write({
            'farmers': ' / '.join(farmers),
            'sample': sample,
            'state': 'ratio',
            'oil_product_id': oil_product.id,
            'shrinkage_location_id': sloc and sloc.id or False
            })

    def ratio2force(self):
        self.ensure_one()
        assert self.state == 'ratio'
        new_state = 'force'
        if len(self.line_ids) == 1:  # Skip force ratio step
            new_state = 'pack'
            if self.oil_destination == 'sale':  # Skip pack
                new_state = 'check'
        self.write({'state': new_state})
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
        variant_modulation = self.env.user.has_group('olive_mill.oil_ratio_modulation_per_olive_variant')
        total_oil_qty = self.oil_qty
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
            if variant_modulation:
                total_olive_prorata_coef = sum([line.variant_id.ratio_coef * line.olive_qty for line in self.line_ids])
                first_line_oil_qty = total_oil_qty * first_line_to_process.olive_qty * first_line_to_process.variant_id.ratio_coef / total_olive_prorata_coef
            else:
                total_olive_prorata = self.olive_qty
                first_line_oil_qty = total_oil_qty * first_line_to_process.olive_qty / total_olive_prorata
            total_oil_prorata = total_oil_qty
        first_line_vals = first_line_to_process._oil_qty_compute_other_vals(
            first_line_oil_qty, first_line_ratio)
        # Write on first line
        first_line_to_process.write(first_line_vals)
        lines = [line for line in self.line_ids if line != first_line_to_process]
        for line in lines:
            # compute oil qty with a pro-rata using special values total_oil_prorata
            # and total_olive_prorata
            if variant_modulation:
                oil_qty = total_oil_prorata * line.olive_qty * line.variant_id.ratio_coef / total_olive_prorata_coef
            else:
                oil_qty = total_oil_prorata * line.olive_qty / total_olive_prorata
            oil_qty_for_ratio = oil_qty
            ratio = float_round(
                100 * oil_qty_for_ratio / line.olive_qty, precision_digits=pr_ratio)
            vals = line._oil_qty_compute_other_vals(oil_qty, ratio)
            # Write on other lines
            line.write(vals)

    def check2done(self):
        self.ensure_one()
        assert self.state == 'check'
        smo = self.env['stock.move']
        pr_oil = self.env['decimal.precision'].precision_get('Olive Oil Volume')
        wloc = self.warehouse_id.olive_withdrawal_loc_id
        stock_loc = self.warehouse_id.lot_stock_id
        sale_loc = self.sale_location_id
        oil_product = self.oil_product_id
        season = self.season_id
        to_shrinkage_tank_oil_qty = 0.0

        # create prod lot
        # No expiry date on olive oil in tanks
        prodlot = self.env["stock.lot"].create({
            'olive_production_id': self.id,
            'product_id': oil_product.id,
            'name': self.name,
            'company_id': self.company_id.id,
            })
        for line in self.line_ids:
            if float_compare(line.withdrawal_oil_qty, 0, precision_digits=pr_oil) > 0:
                # create move from virtual prod > Withdrawal loc
                wmove = smo.create({
                    'olive_oil_production_id': self.id,
                    'company_id': self.company_id.id,
                    'name': _('Olive oil production %s: oil withdrawal related to arrival line %s') % (self.name, line.name),
                    'product_id': oil_product.id,
                    'product_uom': oil_product.uom_id.id,
                    'location_id': oil_product.property_stock_production.id,
                    'location_dest_id': wloc.id,
                    'origin': self.name,
                    'product_uom_qty': line.withdrawal_oil_qty,
                    'picked': True,
                    'move_line_ids': [Command.create({
                        'company_id': self.company_id.id,
                        'product_id': oil_product.id,
                        'product_uom_id': oil_product.uom_id.id,
                        'location_id': oil_product.property_stock_production.id,
                        'location_dest_id': wloc.id,
                        'quantity': line.withdrawal_oil_qty,
                        'lot_id': prodlot.id,
                        'owner_id': line.commercial_partner_id.id,
                        })],
                    })
                wmove._action_done()
                assert wmove.state == 'done'
                line.write({'withdrawal_move_id': wmove.id})
            for extra in line.extra_ids.filtered(lambda x: x.product_id.detailed_type in ('olive_bottle_empty', 'olive_barrel_farmer')):
                if extra.product_id.tracking and extra.product_id.tracking != 'none':
                    raise UserError(_(
                        "Can't select the product '%s' in extra items of "
                        "line %s because it is tracked by lot or serial.")
                        % (extra.product_id.display_name, line.name))
                # For empty plastic bottles, We have to create 2 stock moves:
                # 1. from stock to virtual-prod without owner
                # 2. from virtual-prod to withdrawal with owner_id
                # For inox barrels of farmer, we just have to create stock move n°2
                if extra.product_id.detailed_type == 'olive_bottle_empty':
                    extra_move1 = smo.create({
                        'olive_oil_production_id': self.id,
                        'company_id': self.company_id.id,
                        'name': _('Oil production %s: extra item related to arrival line %s (stock to virtual prod without owner)') % (self.name, line.name),
                        'product_id': extra.product_id.id,
                        'product_uom': extra.product_id.uom_id.id,
                        'location_id': stock_loc.id,
                        'location_dest_id': extra.product_id.property_stock_production.id,
                        'origin': self.name,
                        'product_uom_qty': extra.qty,
                        'picked': True,
                        'move_line_ids': [Command.create({
                            'company_id': self.company_id.id,
                            'product_id': extra.product_id.id,
                            'product_uom_id': extra.product_id.uom_id.id,
                            'location_id': stock_loc.id,
                            'location_dest_id': extra.product_id.property_stock_production.id,
                            'quantity': extra.qty,
                            })],
                        })
                    extra_move1._action_done()
                    assert extra_move1.state == 'done'
                extra_move2 = smo.create({
                    'olive_oil_production_id': self.id,
                    'company_id': self.company_id.id,
                    'name': _('Oil production %s: extra item related to arrival line %s (virtual prod to withdrawal location with owner)') % (self.name, line.name),
                    'product_id': extra.product_id.id,
                    'product_uom': extra.product_id.uom_id.id,
                    'location_id': extra.product_id.property_stock_production.id,
                    'location_dest_id': wloc.id,
                    'origin': self.name,
                    'product_uom_qty': extra.qty,
                    'picked': True,
                    'move_line_ids': [Command.create({
                        'company_id': self.company_id.id,
                        'product_id': extra.product_id.id,
                        'product_uom_id': extra.product_id.uom_id.id,
                        'location_id': extra.product_id.property_stock_production.id,
                        'location_dest_id': wloc.id,
                        'quantity': extra.qty,
                        'owner_id': line.commercial_partner_id.id,
                        })],
                    })
                extra_move2._action_done()
                assert extra_move2.state == 'done'

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
            sale_loc.olive_oil_tank_check(raise_if_empty=False)
            sale_loc.olive_oil_tank_compatibility_check(oil_product, season)
            sale_move = smo.create({
                'olive_oil_production_id': self.id,
                'company_id': self.company_id.id,
                'name': _('Olive oil production %s to sale tank') % self.name,
                'product_id': oil_product.id,
                'product_uom': oil_product.uom_id.id,
                'location_id': oil_product.property_stock_production.id,
                'location_dest_id': sale_loc.id,
                'origin': self.name,
                'product_uom_qty': self.to_sale_tank_oil_qty,
                'picked': True,
                'move_line_ids': [Command.create({
                    'company_id': self.company_id.id,
                    'product_id': oil_product.id,
                    'product_uom_id': oil_product.uom_id.id,
                    'location_id': oil_product.property_stock_production.id,
                    'location_dest_id': sale_loc.id,
                    'quantity': self.to_sale_tank_oil_qty,
                    'lot_id': prodlot.id,
                    })],
                })
            sale_move._action_done()
            assert sale_move.state == 'done'
            prod_vals['sale_move_id'] = sale_move.id

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
                'olive_oil_production_id': self.id,
                'company_id': self.company_id.id,
                'name': _('Olive Oil Production %s: Shrinkage') % self.name,
                'product_id': shrinkage_product.id,
                'product_uom': shrinkage_product.uom_id.id,
                'location_id': shrinkage_product.property_stock_production.id,
                'location_dest_id': shrinkage_loc.id,
                'origin': self.name,
                'product_uom_qty': to_shrinkage_tank_oil_qty,
                'picked': True,
                'move_line_ids': [Command.create({
                    'company_id': self.company_id.id,
                    'product_id': shrinkage_product.id,
                    'product_uom_id': shrinkage_product.uom_id.id,
                    'location_id': shrinkage_product.property_stock_production.id,
                    'location_dest_id': shrinkage_loc.id,
                    'quantity': to_shrinkage_tank_oil_qty,
                    'lot_id': shrinkage_product.shrinkage_prodlot_id.id,
                    })],
                })
            shrinkage_move._action_done()
            assert shrinkage_move.state == 'done'
            prod_vals['shrinkage_move_id'] = shrinkage_move.id
        self.write(prod_vals)
        self._update_arrival_production_done()

    def _update_arrival_production_done(self):
        self.ensure_one()
        oalo = self.env['olive.arrival.line']
        oao = self.env['olive.arrival']
        arrivals = oao
        for line in self.line_ids:
            arrivals |= line.arrival_id
        assert arrivals
        arrivals_res = oalo._read_group(
            [('production_state', '=', 'done'), ('arrival_id', 'in', arrivals.ids)],
            groupby=['arrival_id'],
            aggregates=['oil_qty_net:sum', 'olive_qty:sum'])
        for arrival, oil_qty_net, olive_qty in arrivals_res:
            olive_qty_pressed = olive_qty
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
        return super().unlink()

    def detach_lines(self):
        self.ensure_one()
        self.palox_ids.write({'oil_product_id': self.oil_product_id.id})
        self.line_ids.write({'production_id': False})

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

    def open_move_lines(self):
        self.ensure_one()
        mlines = self.env['stock.move.line'].search([('olive_oil_production_id', '=', self.id)])
        action = self.env['ir.actions.actions']._for_xml_id('stock.stock_move_line_action')
        action['domain'] = [('id', 'in', mlines.ids)]
        action['context'] = {'create': 0}
        return action
