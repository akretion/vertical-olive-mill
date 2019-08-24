# -*- coding: utf-8 -*-
# Copyright 2019 Barroux Abbey (http://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
import odoo.addons.decimal_precision as dp


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
        default=lambda self: self.env['olive.season'].get_current_season())
    partner_id = fields.Many2one(
        'res.partner', string='Olive Farmer', required=True, index=True,
        domain=[('parent_id', '=', False), ('olive_farmer', '=', True)])
    commercial_partner_id = fields.Many2one(
        related='partner_id.commercial_partner_id', readonly=True, store=True)
    partner_olive_culture_type = fields.Selection(
        related='partner_id.commercial_partner_id.olive_culture_type', readonly=True)
    partner_organic_certified_logo = fields.Binary(
        related='partner_id.commercial_partner_id.olive_organic_certified_logo',
        readonly=True)
    olive_qty = fields.Integer(
        string='Olive Qty (kg)', required=True)
    oil_product_id = fields.Many2one(
        'product.product', string='Oil Type', index=True,
        domain=[('olive_type', '=', 'oil')])
    sale_olive_qty = fields.Integer(
        string='Sale Olive Qty (kg)', required=True)
    oil_qty = fields.Integer(
        compute='_compute_oil_qty', string='Oil Qty (L)', store=True)
    sale_oil_qty = fields.Integer(
        compute='_compute_oil_qty', string='Sale Oil Qty (L)', store=True)
    past_average_ratio = fields.Float(
        compute='_compute_past_average',
        digits=dp.get_precision('Olive Oil Ratio'), store=True,
        string='Past Average Ratio (%)')
    past_average_olive_qty = fields.Integer(
        compute='_compute_past_average', store=True,
        string='Past Average Olive Qty (kg)')
    past_average_oil_qty = fields.Integer(
        compute='_compute_past_average', store=True,
        string='Past Average Oil Qty (L)')
    past_average_sale_olive_qty = fields.Integer(
        compute='_compute_past_average', store=True,
        string='Past Average Sale Olive Qty (kg)')
    past_average_sale_oil_qty = fields.Integer(
        compute='_compute_past_average', store=True,
        string='Past Average Sale Oil Qty (L)')

    _sql_constraints = [
        ('partner_season_unique',
         'unique(partner_id, season_id)',
         'There is already a poll for this olive farmer for the same season.'),
        ('sale_inferior',
         'CHECK(olive_qty - sale_olive_qty >= 0)',
         'The sale olive quantity cannot be superior to the olive quantity.'),
        ]

    @api.depends('past_average_ratio', 'olive_qty', 'sale_olive_qty')
    def _compute_oil_qty(self):
        for poll in self:
            # TODO when poll.past_average_ratio is null because there is no past
            poll.oil_qty = poll.olive_qty * poll.past_average_ratio / 100.0
            poll.sale_oil_qty = poll.sale_olive_qty * poll.past_average_ratio / 100.0

    @api.depends('partner_id', 'season_id')
    def _compute_past_average(self):
        for poll in self:
            past_average_ratio = 0.0
            past_average_olive_qty = 0.0
            past_average_oil_qty = 0.0
            past_average_sale_oil_qty = 0.0
            past_average_sale_olive_qty = 0.0
            season = self.season_id
            company = poll.company_id
            limit = company.olive_poll_average_season_count
            past_seasons = self.env['olive.season'].search([
                ('company_id', '=', company.id),
                ('start_date', '<', season.start_date),
                ], order='start_date desc', limit=limit)
            res = self.env['olive.arrival.line'].read_group([
                ('season_id', 'in', past_seasons.ids),
                ('state', '=', 'done'),
                ('production_state', '=', 'done'),
                ('commercial_partner_id', '=', poll.commercial_partner_id.id)],
                ['olive_qty', 'oil_qty_with_compensation',
                 'sale_oil_qty', 'season_id'],
                ['season_id'])
            # caution: an olive farmer may not have arrivals during each season
            # We do the average on the seasons where he made at least 1 arrival
            season_count = len(res)
            olive_qty = 0.0
            oil_qty_with_compensation = 0.0
            sale_oil_qty = 0.0
            for re in res:
                olive_qty += re['olive_qty']
                oil_qty_with_compensation += re['oil_qty_with_compensation']
                sale_oil_qty += re['sale_oil_qty']
            if season_count:
                season_count = float(season_count)
                past_average_olive_qty = olive_qty / season_count
                past_average_oil_qty = oil_qty_with_compensation / season_count
                past_average_sale_oil_qty = sale_oil_qty / season_count
            if oil_qty_with_compensation > 0:
                past_average_ratio = 100 * oil_qty_with_compensation / olive_qty
            if past_average_ratio > 0:
                past_average_sale_olive_qty =\
                    past_average_sale_oil_qty * 100 / past_average_ratio
            poll.past_average_ratio = past_average_ratio
            poll.past_average_olive_qty = int(round(past_average_olive_qty))
            poll.past_average_oil_qty = int(round(past_average_oil_qty))
            poll.past_average_sale_oil_qty = int(round(past_average_sale_oil_qty))
            poll.past_average_sale_olive_qty = int(round(past_average_sale_olive_qty))

    @api.depends('partner_id', 'season_id')
    def name_get(self):
        res = []
        for rec in self:
            name = '%s - %s' % (rec.season_id.name, rec.partner_id.display_name)
            res.append((rec.id, name))
        return res
