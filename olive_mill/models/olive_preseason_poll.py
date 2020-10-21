# -*- coding: utf-8 -*-
# Copyright 2019 Barroux Abbey (http://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
import odoo.addons.decimal_precision as dp
from odoo.tools import float_is_zero


class OlivePreseasonPoll(models.Model):
    _name = 'olive.preseason.poll'
    _description = 'Pre-season polls'
    _order = 'season_id desc, id desc'

    company_id = fields.Many2one(
        'res.company', string='Company',
        ondelete='cascade', required=True,
        default=lambda self: self.env['res.company']._company_default_get())
    season_id = fields.Many2one(
        'olive.season', string='Season', required=True, index=True,
        default=lambda self: self.env.user.company_id.current_season_id.id)
    partner_id = fields.Many2one(
        'res.partner', string='Olive Farmer', required=True, index=True,
        domain=[('parent_id', '=', False), ('olive_farmer', '=', True)])
    olive_culture_type = fields.Selection(
        related='partner_id.commercial_partner_id.olive_culture_type', readonly=True)
    commercial_partner_id = fields.Many2one(
        related='partner_id.commercial_partner_id', readonly=True, store=True)
    olive_organic_certified_logo = fields.Binary(
        related='partner_id.commercial_partner_id.olive_organic_certified_logo',
        readonly=True)
    line_ids = fields.One2many(
        'olive.preseason.poll.line', 'poll_id', string='Lines')
    past_data_ok = fields.Boolean(readonly=True)
    n1_season_id = fields.Many2one(
        'olive.season', readonly=True, string='N-1 Season')
    n1_ratio_net = fields.Float(
        string='N-1 Net Ratio (%)',
        digits=dp.get_precision('Olive Oil Ratio'), readonly=True)
    n1_olive_qty = fields.Integer(
        string='N-1 Olive Qty (kg)', readonly=True)
    n1_oil_qty_net = fields.Integer(
        string='N-1 Net Oil Qty (L)', readonly=True)
    n1_sale_olive_qty = fields.Integer(
        string='N-1 Sale Olive Qty (kg)', readonly=True)
    n1_sale_oil_qty = fields.Integer(
        string='N-1 Sale Oil Qty (L)', readonly=True)
    n2_season_id = fields.Many2one(
        'olive.season', readonly=True, string='N-2 Season')
    n2_ratio_net = fields.Float(
        string='N-2 Net Ratio (%)',
        digits=dp.get_precision('Olive Oil Ratio'), readonly=True)
    n2_olive_qty = fields.Integer(
        string='N-2 Olive Qty (kg)', readonly=True)
    n2_oil_qty_net = fields.Integer(
        string='N-2 Net Oil Qty (L)', readonly=True)
    n2_sale_olive_qty = fields.Integer(
        string='N-2 Sale Olive Qty (kg)', readonly=True)
    n2_sale_oil_qty = fields.Integer(
        string='N-2 Sale Oil Qty (L)', readonly=True)
    n3_season_id = fields.Many2one(
        'olive.season', readonly=True, string='N-3 Season')
    n3_ratio_net = fields.Float(
        string='N-3 Net Ratio (%)',
        digits=dp.get_precision('Olive Oil Ratio'), readonly=True)
    n3_olive_qty = fields.Integer(
        string='N-3 Olive Qty (kg)', readonly=True)
    n3_oil_qty_net = fields.Integer(
        string='N-3 Net Oil Qty (L)', readonly=True)
    n3_sale_olive_qty = fields.Integer(
        string='N-3 Sale Olive Qty (kg)', readonly=True)
    n3_sale_oil_qty = fields.Integer(
        string='N-3 Sale Oil Qty (L)', readonly=True)
    past_average_ratio_net = fields.Float(
        digits=dp.get_precision('Olive Oil Ratio'), readonly=True,
        string='Past Average Net Ratio (%)')
    past_average_olive_qty = fields.Integer(
        string='Past Average Olive Qty (kg)', readonly=True)
    past_average_oil_qty_net = fields.Integer(
        string='Past Average Net Oil Qty (L)', readonly=True)
    past_average_sale_olive_qty = fields.Integer(
        string='Past Average Sale Olive Qty (kg)', readonly=True)
    past_average_sale_oil_qty = fields.Integer(
        string='Past Average Sale Oil Qty (L)', readonly=True)

    _sql_constraints = [(
        'partner_season_unique',
        'unique(partner_id, season_id)',
        'There is already a poll for this olive farmer for the same season.')]

    @api.depends('past_average_ratio', 'olive_qty', 'sale_olive_qty')
    def _compute_oil_qty(self):
        for poll in self:
            # TODO when poll.past_average_ratio is null because there is no past
            poll.oil_qty = poll.olive_qty * poll.past_average_ratio / 100.0
            poll.sale_oil_qty = poll.sale_olive_qty * poll.past_average_ratio / 100.0

    @api.onchange('partner_id')
    def partner_id_change(self):
        if self.partner_id and self.past_data_ok:
            self.past_data_ok = False

    def update_past_data(self):
        self.ensure_one()
        oso = self.env['olive.season']
        prec = self.env['decimal.precision'].precision_get('Olive Weight')
        vals = {
            'past_data_ok': True,
            'past_average_ratio_net': 0.0,
            'past_average_olive_qty': 0.0,
            'past_average_oil_qty_net': 0.0,
            'past_average_sale_oil_qty': 0.0,
            'past_average_sale_olive_qty': 0.0,
            }
        season = self.season_id
        company = self.company_id
        for i in ['n1', 'n2', 'n3']:
            for suffix in ['season_id', 'ratio_net', 'olive_qty', 'oil_qty_net', 'sale_olive_qty', 'sale_oil_qty']:
                field_name = '%s_%s' % (i, suffix)
                vals[field_name] = False
        past_seasons = self.env['olive.season'].search([
            ('company_id', '=', company.id),
            ('start_date', '<', season.start_date),
            ], order='start_date desc', limit=3)
        res = self.env['olive.arrival.line'].read_group([
            ('season_id', 'in', past_seasons.ids),
            ('state', '=', 'done'),
            ('production_state', '=', 'done'),
            ('commercial_partner_id', '=', self.commercial_partner_id.id)],
            ['olive_qty', 'oil_qty_net', 'sale_oil_qty', 'season_id'],
            ['season_id'])
        season2data = {}
        for re in res:
            season_id = re['season_id'][0]
            season = oso.browse(season_id)
            if not float_is_zero(re['olive_qty'], precision_digits=prec):
                season2data[season] = {
                    'olive_qty': re['olive_qty'],
                    'sale_oil_qty': re['sale_oil_qty'],
                    'oil_qty_net': re['oil_qty_net'],
                    }
        # caution: an olive farmer may not have arrivals during each season
        # We do the average on the seasons where he made at least 1 arrival
        season_count = 0
        i = 0
        for season in past_seasons:
            i += 1
            prefix = 'n%d_' % i
            vals[prefix + 'season_id'] = season.id
            if season in season2data:
                season_count += 1
                for field_name in ['olive_qty', 'oil_qty_net', 'sale_oil_qty']:
                    vals[prefix + field_name] = season2data[season][field_name]
                    vals['past_average_' + field_name] += season2data[season][field_name]
                vals[prefix + 'ratio_net'] = 100 * vals[prefix + 'oil_qty_net'] / vals[prefix + 'olive_qty']
                if vals[prefix + 'ratio_net'] > 0:
                    vals[prefix + 'sale_olive_qty'] = vals[prefix + 'sale_oil_qty'] * 100 / vals[prefix + 'ratio_net']
        # Finalize average computation
        if season_count:
            vals['past_average_ratio_net'] = 100 * vals['past_average_oil_qty_net'] / vals['past_average_olive_qty']
            if vals['past_average_ratio_net'] > 0:
                vals['past_average_sale_olive_qty'] = vals['past_average_sale_oil_qty'] * 100 / vals['past_average_ratio_net']
            vals['past_average_olive_qty'] = vals['past_average_olive_qty'] / season_count
            vals['past_average_oil_qty_net'] = vals['past_average_oil_qty_net'] / season_count
            vals['past_average_sale_oil_qty'] = vals['past_average_sale_oil_qty'] / season_count
        self.write(vals)

    @api.depends('partner_id', 'season_id')
    def name_get(self):
        res = []
        for rec in self:
            name = '%s - %s' % (rec.season_id.name, rec.partner_id.display_name)
            res.append((rec.id, name))
        return res

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(OlivePreseasonPoll, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        return self.env.user.company_id.current_season_update(res, view_type)


class OlivePreseasonPollLine(models.Model):
    _name = 'olive.preseason.poll.line'
    _description = 'Pre-season polls Line'

    poll_id = fields.Many2one(
        'olive.preseason.poll', string='Pre-Season Poll', ondelete='cascade')
    olive_qty = fields.Integer(
        string='Olive Qty (kg)', required=True)
    oil_product_id = fields.Many2one(
        'product.product', string='Oil Type', index=True,
        domain=[('olive_type', '=', 'oil')])
    sale_olive_qty = fields.Integer(
        string='Sale Olive Qty (kg)', required=True)
    oil_qty = fields.Integer(string='Oil Qty (L)')
    sale_oil_qty = fields.Integer(string='Sale Oil Qty (L)')
    olive_culture_type = fields.Selection(
        related='poll_id.partner_id.commercial_partner_id.olive_culture_type', readonly=True)
    commercial_partner_id = fields.Many2one(
        related='poll_id.partner_id.commercial_partner_id', store=True,
        string='Olive Farmer')
    season_id = fields.Many2one(related='poll_id.season_id', store=True)

    _sql_constraints = [(
        'partner_season_oil_product_unique',
        'unique(commercial_partner_id, season_id, oil_product_id)',
        'Same oil type selected twice.'
        ), (
        'sale_inferior',
        'CHECK(olive_qty - sale_olive_qty >= 0)',
        'The sale olive quantity cannot be superior to the olive quantity.'
        )]

    def _get_ratio(self):
        self.ensure_one()
        prec = self.env['decimal.precision'].precision_get('Olive Oil Ratio')
        poll = self.poll_id
        ratio = poll.past_average_ratio_net
        if float_is_zero(ratio, precision_digits=prec):
            ratio = poll.company_id.olive_preseason_poll_ratio_no_history
        return ratio

    @api.onchange('olive_qty')
    def olive_qty_change(self):
        if not self._context.get('olive_onchange'):
            self.env.context = self.with_context(olive_onchange=True).env.context
            self.oil_qty = int(self.olive_qty * self._get_ratio() / 100)

    @api.onchange('oil_qty')
    def oil_qty_change(self):
        if not self._context.get('olive_onchange'):
            ratio = self._get_ratio()
            if ratio > 0:
                self.env.context = self.with_context(olive_onchange=True).env.context
                self.olive_qty = int(self.oil_qty * 100 / ratio)

    @api.onchange('sale_olive_qty')
    def sale_olive_qty_change(self):
        if not self._context.get('sale_olive_onchange'):
            self.env.context = self.with_context(sale_olive_onchange=True).env.context           
            self.sale_oil_qty = int(self.sale_olive_qty * self._get_ratio() / 100)

    @api.onchange('sale_oil_qty')
    def sale_oil_qty_onchange(self):
        if not self._context.get('sale_olive_onchange'):
            ratio = self._get_ratio()
            if ratio > 0:
                self.env.context = self.with_context(sale_olive_onchange=True).env.context
                self.sale_olive_qty = int(100 * self.sale_oil_qty / ratio)

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(OlivePreseasonPollLine, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        return self.env.user.company_id.current_season_update(res, view_type)
