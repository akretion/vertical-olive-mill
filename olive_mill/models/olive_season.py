# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_round
from dateutil.relativedelta import relativedelta
from babel.dates import format_date
import json


class OliveSeason(models.Model):
    _name = 'olive.season'
    _description = 'Olive Season'
    _order = 'start_date desc'

    name = fields.Char(string='Name', required=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env['res.company']._company_default_get())
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    year = fields.Char(compute='_compute_year', string='Year', store=True)
    early_bird_date = fields.Date(string='Early Bird Limit Date')
    default_expiry_date = fields.Date(string='Default Oil Expiry Date')
    olive_qty_arrived = fields.Integer(
        compute='_compute_totals', string='Arrived Olive Qty (kg)', readonly=True)
    olive_qty = fields.Integer(
        compute='_compute_totals', string='Pressed Olive Qty (kg)', readonly=True)
    sale_oil_qty = fields.Integer(
        compute='_compute_totals', string='Sale Oil Qty (L)', readonly=True)
    oil_qty_with_compensation = fields.Integer(
        compute='_compute_totals', string='Oil Qty with Compensation (L)', readonly=True)
    withdrawal_oil_qty = fields.Integer(
        compute='_compute_totals', string='Withdrawal Oil Qty (L)', readonly=True)
    gross_ratio = fields.Float(
        compute='_compute_totals', string='Gross Ratio (%)', readonly=True,
        digits=dp.get_precision('Olive Oil Ratio'))
    show_on_dashboard = fields.Boolean(string='Show on Dashboard', default=True)
    kanban_dashboard_graph = fields.Text(compute='_compute_kanban_dashboard_graph')
    partner_organic_certif_generated = fields.Boolean(readonly=True)

    _sql_constrains = [(
        'name_unique',
        'unique(name, company_id)',
        'This season name already exists in this company.')]

    @api.depends('start_date')
    def _compute_year(self):
        for season in self:
            season.year = season.start_date[:4]

    def _compute_totals(self):
        oalo = self.env['olive.arrival.line']
        pr_ratio = self.env['decimal.precision'].precision_get(
            'Olive Oil Ratio')
        arrival_res = oalo.read_group([
            ('season_id', 'in', self.ids),
            ('state', '=', 'done')],
            ['season_id', 'olive_qty'], ['season_id'])
        for arrival_re in arrival_res:
            season = self.browse(arrival_re['season_id'][0])
            season.olive_qty_arrived = arrival_re['olive_qty']
        arrival_prod_done_res = oalo.read_group([
            ('season_id', 'in', self.ids),
            ('production_state', '=', 'done')],
            ['season_id', 'olive_qty', 'oil_qty_with_compensation', 'sale_oil_qty', 'withdrawal_oil_qty'],
            ['season_id'])
        for re in arrival_prod_done_res:
            season = self.browse(re['season_id'][0])
            olive_qty = re['olive_qty']
            oil_qty_with_compensation = re['oil_qty_with_compensation']
            gross_ratio = 0
            if olive_qty:
                gross_ratio = float_round(
                    100 * oil_qty_with_compensation / olive_qty,
                    precision_digits=pr_ratio)
            season.olive_qty = int(round(olive_qty))
            season.oil_qty_with_compensation = int(round(oil_qty_with_compensation))
            season.gross_ratio = gross_ratio
            season.sale_oil_qty = int(round(re['sale_oil_qty']))
            season.withdrawal_oil_qty = int(round(re['withdrawal_oil_qty']))

    @api.constrains('start_date', 'end_date', 'early_bird_date')
    def season_check(self):
        for season in self:
            if season.end_date <= season.start_date:
                raise ValidationError(_(
                    "End Date must be after Start Date on season '%s'")
                    % season.name)
            if season.early_bird_date:
                if season.early_bird_date <= season.start_date:
                    raise ValidationError(_(
                        "On season '%s', the Early Bird Date (%s) must be "
                        "after the Start Date (%s).") % (
                            season.name, season.early_bird_date,
                            season.start_date))
                if season.early_bird_date >= season.end_date:
                    raise ValidationError(_(
                        "On season '%s', the Early Bird Date (%s) must be "
                        "before the End Date (%s).") % (
                            season.name, season.early_bird_date,
                            season.end_date))
            oseasons = self.search([
                ('year', '=', season.year),
                ('id', '!=', season.id)])
            if oseasons:
                raise ValidationError(_(
                    "Season '%s' (%s to %s) is attached to the same year "
                    "as season '%s'.") % (
                        oseasons[0].name, oseasons[0].start_date,
                        oseasons[0].end_date, season.name))

    @api.onchange('start_date')
    def start_date_change(self):
        if self.start_date:
            start_date_dt = fields.Date.from_string(self.start_date)
            expiry_date_dt = start_date_dt + relativedelta(
                month=1, years=3, day=1)
            self.default_expiry_date = fields.Date.to_string(expiry_date_dt)

    @api.model
    def get_current_season(self):
        return self.env.user.company_id.get_current_season()

    def _compute_kanban_dashboard_graph(self):
        for season in self:
            data = []
            start_date_dt = fields.Date.from_string(season.start_date)
            end_date_dt = fields.Date.from_string(season.end_date)
            today_dt = fields.Date.from_string(fields.Date.context_today(self))
            if today_dt < end_date_dt:
                end_date_dt = today_dt
            query = """
            SELECT date, sum(olive_qty) as olive_qty
            FROM olive_arrival
            WHERE date >= %s
            AND date <= %s
            AND season_id = %s
            GROUP BY date
            ORDER BY date
            """
            self.env.cr.execute(query, (start_date_dt, end_date_dt, season.id))
            sql_res = self.env.cr.dictfetchall()
            date2qty = {}
            for sql_re in sql_res:
                date2qty[fields.Date.from_string(sql_re['date'])] = sql_re['olive_qty']
            locale = self._context.get('lang') or 'en_US'
            cur_date_dt = start_date_dt
            while cur_date_dt <= end_date_dt:
                name = format_date(cur_date_dt, 'd LLLL Y', locale=locale)
                short_name = format_date(cur_date_dt, 'd MMM', locale=locale)
                data.append({
                    'x': short_name,
                    'y': date2qty.get(cur_date_dt, 0),
                    'name': name,
                    })
                cur_date_dt += relativedelta(days=1)
            # from pprint import pprint
            # pprint(data)
            res = [{'values': data, 'area': True}]
            season.kanban_dashboard_graph = json.dumps(res)

    def dashboard_open_action(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window'].for_xml_id(
            'olive_mill', 'olive_arrival_line_action')
        action.update({
            'context': {
                'search_default_season_id': self.id,
                'search_default_production_done': True,
                },
            'views': False,
            })
        return action

    def generate_partner_organic_certif(self):
        self.ensure_one()
        # Get all partners that already had 1 organic certif in the past
        # Then look at the last arrival
        # If they had a valid organic certif for their last arrival
        # then we generate a draft organic certif
        poco = self.env['partner.organic.certification']
        rpo = self.env['res.partner']
        oao = self.env['olive.arrival']
        existing_cert = poco.search([('season_id', '=', self.id)])
        if existing_cert:
            raise UserError(_(
                "Some certifications have already been generated for season '%s'.")
                % self.name)
        rg_res = poco.read_group(
            [('state', '=', 'done')], ['partner_id'], ['partner_id'])
        cert_ids = []
        for rg_re in rg_res:
            partner = rpo.browse(rg_re['partner_id'][0])
            if partner.active and partner.olive_farmer and not partner.parent_id:
                last_arrival = oao.search([
                    ('state', '=', 'done'),
                    ('season_id', '!=', self.id),
                    ('commercial_partner_id', '=', partner.id),
                    ], order='date desc', limit=1)
                if last_arrival:
                    cert = poco.search([
                        ('state', '=', 'done'),
                        ('season_id', '=', last_arrival.season_id.id),
                        ('partner_id', '=', partner.id)], limit=1)
                    if cert:
                        new_cert = poco.create({
                            'partner_id': partner.id,
                            'season_id': self.id,
                            'state': 'draft',
                            'conversion': cert.conversion,
                            'certifying_entity_id': cert.certifying_entity_id.id,
                            })
                        cert_ids.append(new_cert.id)
        if not cert_ids:
            raise UserError(_("No organic certification generated."))
        self.partner_organic_certif_generated = True
        action = self.env.ref('olive_mill.partner_organic_certification_action').read()[0]
        action.update({
            'context': {'partner_organic_certification_main_view': True},
            'domain': [('id', 'in', cert_ids)],
            })
        return action
