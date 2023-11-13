# Copyright 2019-2023 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
from odoo.tools.misc import formatLang


class OliveOilAnalysis(models.Model):
    _name = 'olive.oil.analysis'
    _description = 'Olive Oil Analysis'
    _order = 'id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _check_company_auto = True

    name = fields.Char(string='Analysis Number', index=True, readonly=True, default=lambda x: _('New'))
    oil_source_type = fields.Selection([
        ('arrival', 'Arrival'),
        ('tank', 'Tank'),
        ], default='arrival', string='Oil Source Type', required=True,
        tracking=True, states={'done': [('readonly', True)]})
    arrival_line_id = fields.Many2one(
        'olive.arrival.line', string='Arrival Line',
        states={'done': [('readonly', True)]}, tracking=True, check_company=True)
    partner_id = fields.Many2one(
        related='arrival_line_id.arrival_id.partner_id.commercial_partner_id',
        store=True, index=True, string='Olive Farmer')
    oil_product_id = fields.Many2one(
        'product.product', string='Oil Type', required=True, index=True,
        domain=[('detailed_type', '=', 'olive_oil')],
        tracking=True, states={'done': [('readonly', True)]})
    lot_id = fields.Many2one(
        'stock.production.lot', string='Oil Lot',
        tracking=True, states={'done': [('readonly', True)]},
        domain="[('product_id', '=', oil_product_id), ('company_id', '=', company_id)]",
        check_company=True)
    production_id = fields.Many2one(
        related='arrival_line_id.production_id', store=True)
    production_date = fields.Date(
        related='arrival_line_id.production_id.date', store=True,
        string='Production Date')
    arrival_date = fields.Date(
        related='arrival_line_id.arrival_id.date', store=True)
    season_id = fields.Many2one(
        'olive.season', string='Season', required=True, index=True,
        domain="[('company_id', '=', company_id)]",
        states={'done': [('readonly', True)]}, check_company=True)
    current_season = fields.Boolean(
        compute='_compute_current_season', search='_search_current_season')
    location_id = fields.Many2one(
        'stock.location', string='Oil Tank',
        domain="[('olive_tank_type', '!=', False), ('company_id', '=', company_id)]",
        states={'done': [('readonly', True)]}, tracking=True, check_company=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('cancel', 'Cancel'),
        ], string='State', readonly=True, default='draft', copy=False,
        tracking=True)
    date = fields.Date(
        string='Analysis Date', states={'done': [('readonly', True)]},
        copy=False, tracking=True)
    execution_mode = fields.Selection([
        ('internal', 'Internal'),
        ('external', 'External'),
        ], default='internal', string='Execution Mode', required=True,
        states={'done': [('readonly', True)]}, tracking=True)
    execution_user_id = fields.Many2one(
        'res.users', string='Analysis Made by',
        states={'done': [('readonly', True)]}, tracking=True,
        default=lambda self: self.env.company.olive_oil_analysis_default_user_id.id or False)
    execution_partner_id = fields.Many2one(
        'res.partner', string='Analysis Made by (Partner)',
        states={'done': [('readonly', True)]}, tracking=True,
        domain=[('supplier', '=', True)])
    company_id = fields.Many2one(
        'res.company', string='Company',
        ondelete='cascade', required=True,
        states={'done': [('readonly', True)]},
        default=lambda self: self.env.company)
    line_ids = fields.One2many(
        'olive.oil.analysis.line', 'analysis_id', string='Analysis Lines',
        states={'done': [('readonly', True)]})

    def _compute_current_season(self):
        for ana in self:
            if ana.company_id.current_season_id == ana.season_id:
                ana.current_season = True
            else:
                ana.current_season = False

    def _search_current_season(self, operator, value):
        return self.env['res.company']._search_current_season(operator, value)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'company_id' in vals:
                self = self.with_company(vals['company_id'])
            if vals.get('name', _("New")) == _("New"):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'olive.oil.analysis', sequence_date=vals.get('date')) or _("New")
        return super().create(vals)

    @api.onchange('location_id')
    def location_id_change(self):
        if self.oil_source_type == 'tank' and self.location_id:
            self.season_id = self.location_id.olive_season_id
            self.oil_product_id = self.location_id.oil_product_id
            # if oil tank is merged
            quant_lot_rg = self.env['stock.quant'].read_group(
                [('location_id', '=', self.location_id.id)],
                ['qty', 'lot_id'], ['lot_id'])
            if len(quant_lot_rg) == 1 and quant_lot_rg[0].get('lot_id'):
                self.lot_id = quant_lot_rg[0]['lot_id'][0]
            else:
                self.lot_id = False

    @api.onchange('arrival_line_id')
    def arrival_line_id_change(self):
        if self.oil_source_type == 'arrival' and self.arrival_line_id:
            self.season_id = self.arrival_line_id.season_id
            self.oil_product_id = self.arrival_line_id.oil_product_id
            self.lot_id = False

    @api.onchange('execution_mode')
    def execution_mode_change(self):
        if self.execution_mode == 'external' and self.execution_user_id:
            self.execution_user_id = False
        elif self.execution_mode == 'internal' and self.execution_partner_id:
            self.execution_partner_id = False

    def validate(self):
        today = fields.Date.context_today(self)
        for ana in self:
            if ana.execution_mode == 'internal' and not ana.execution_user_id:
                raise UserError(_(
                    'On analysis %s, you must set the user who made '
                    'the analysis.') % ana.display_name)
            if ana.execution_mode == 'external' and not ana.execution_partner_id:
                raise UserError(_(
                    'On analysis %s, you must set the partner who mode '
                    'the analysis.') % ana.display_name)
            if not ana.date:
                raise UserError(_(
                    'On analysis %s, you must set the analysis date.')
                    % ana.display_name)
            if ana.date > today:
                raise UserError(_(
                    'On analysis %s, the analysis date is in the future.')
                    % ana.display_name)
            if not ana.line_ids:
                raise UserError(_(
                    'Analysis %s has no lines.') % ana.display_name)
            for line in ana.line_ids:
                if not line.result_int and float_is_zero(line.result_p1, precision_digits=1) and float_is_zero(line.result_p2, precision_digits=2):
                    raise UserError(_(
                        "On analysis %s, you must enter the result for the "
                        "analysis '%s'.") % (
                            ana.display_name, line.product_id.name))
        self.write({'state': 'done'})

    def unlink(self):
        for ana in self:
            if ana.state == 'done':
                raise UserError(_(
                    "You cannot delete analysis '%s' because it is in done state.")
                    % ana.display_name)
        return super().unlink()

    def back2draft(self):
        self.write({'state': 'draft'})

    def cancel(self):
        self.write({'state': 'cancel'})


class OliveOilAnalysisLine(models.Model):
    _name = 'olive.oil.analysis.line'
    _description = 'Olive Oil Analysis Line'

    analysis_id = fields.Many2one(
        'olive.oil.analysis', ondelete='cascade', string='Analysis')
    product_id = fields.Many2one(
        'product.product', string='Analysis Type',
        required=True, states={'done': [('readonly', True)]},
        domain=[('detailed_type', '=', 'olive_analysis')])
    decimal_precision = fields.Integer(
        compute='_compute_params', readonly=False, store=True,
        string='Decimal Precision', states={'done': [('readonly', True)]})
    result_p1 = fields.Float(
        string='Result (1 decimal)', digits=(16, 1),
        states={'done': [('readonly', True)]}, group_operator='avg')
    result_p2 = fields.Float(
        string='Result (2 decimals)', digits=(16, 2),
        states={'done': [('readonly', True)]}, group_operator='avg')
    result_int = fields.Integer(
        string='Result (integer)',
        states={'done': [('readonly', True)]}, group_operator='avg')
    result_string = fields.Char(
        string='Result', compute='_compute_result_string', readonly=True)
    precision = fields.Char(
        compute='_compute_params', readonly=False, store=True,
        string='Precision', states={'done': [('readonly', True)]})
    instrument = fields.Char(
        compute='_compute_params', readonly=False, store=True,
        string='Instrument', states={'done': [('readonly', True)]})
    uom = fields.Char(related='product_id.olive_analysis_uom', string='Unit of Measure')
    oil_source_type = fields.Selection(
        related='analysis_id.oil_source_type', store=True)
    oil_product_id = fields.Many2one(
        related='analysis_id.oil_product_id', store=True, index=True)
    date = fields.Date(related='analysis_id.date', store=True)
    season_id = fields.Many2one(related='analysis_id.season_id', store=True)
    current_season = fields.Boolean(
        compute='_compute_current_season', search='_search_current_season')
    partner_id = fields.Many2one(
        related='analysis_id.arrival_line_id.arrival_id.partner_id.commercial_partner_id',
        store=True, index=True, string='Olive Farmer')
    location_id = fields.Many2one(related='analysis_id.location_id', store=True)
    state = fields.Selection(related='analysis_id.state', store=True)
    execution_mode = fields.Selection(related='analysis_id.execution_mode', store=True)

    @api.depends('product_id')
    def _compute_params(self):
        for line in self:
            instrument = precision = decimal_precision = False
            if line.product_id:
                instrument = line.product_id.olive_analysis_instrument
                precision = line.product_id.olive_analysis_precision
                decimal_precision = line.product_id.olive_analysis_decimal_precision
            line.instrument = instrument
            line.precision = precision
            line.decimal_precision = decimal_precision

    @api.depends('decimal_precision', 'result_p1', 'result_p2', 'result_int')
    def _compute_result_string(self):
        for line in self:
            res = 'Decimal precision not supported'
            lang = line.analysis_id.company_id.partner_id.lang
            env_lang = line.with_context(lang=lang).env
            if line.decimal_precision == 0:
                res = formatLang(env_lang, line.result_int, digits=0)
            elif line.decimal_precision == 1:
                res = formatLang(env_lang, round(line.result_p1, 1), digits=1)
            elif line.decimal_precision == 2:
                res = formatLang(env_lang, round(line.result_p2, 2), digits=2)
            line.result_string = res

    def _compute_current_season(self):
        for line in self:
            if line.company_id.current_season_id == line.season_id:
                line.current_season = True
            else:
                line.current_season = False

    def _search_current_season(self, operator, value):
        return self.env['res.company']._search_current_season(operator, value)
