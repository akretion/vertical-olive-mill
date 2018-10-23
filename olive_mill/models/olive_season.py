# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class OliveSeason(models.Model):
    _name = 'olive.season'
    _description = 'Olive Season'
    _order = 'start_date desc'

    name = fields.Char(string='Name', required=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env['res.company']._company_default_get(
            'olive.season'))
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    year = fields.Char(compute='_compute_year', string='Year', store=True)
    early_bird_date = fields.Date(string='Early Bird Limit Date')
    default_expiry_date = fields.Date(string='Default Oil Expiry Date')

    _sql_constrains = [(
        'name_unique',
        'unique(name, company_id)',
        'This season name already exists in this company.')]

    @api.depends('start_date')
    def _compute_year(self):
        for season in self:
            season.year = season.start_date[:4]

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
            # TODO is it really a good idea ?
            oseasons = self.search([
                ('end_date', '>', season.start_date),
                ('id', '!=', season.id)])
            if oseasons:
                raise ValidationError(_(
                    "Season '%s' (%s to %s) is after or over this "
                    "season (%s)") % (
                        oseasons[0].name, oseasons[0].start_date,
                        oseasons[0].end_date, season.name))

    @api.onchange('end_date')
    def end_date_change(self):
        if self.end_date and not self.default_expiry_date:
            end_date_dt = fields.Date.from_string(self.end_date)
            if end_date_dt.month == 12:
                expiry_date_dt = end_date_dt + relativedelta(
                    month=1, years=3, day=1)
            else:
                expiry_date_dt = end_date_dt + relativedelta(
                    month=1, years=2, day=1)
            self.default_expiry_date = fields.Date.to_string(expiry_date_dt)

    @api.model
    def get_current_season(self):
        today = fields.Date.context_today(self)
        seasons = self.search([
            ('start_date', '<=', today),
            ('end_date', '>=', today),
            ('company_id', '=', self.env.user.company_id.id),
            ])
        if seasons:
            return seasons[0]
        seasons = self.search([
            ('start_date', '<=', today),
            ('company_id', '=', self.env.user.company_id.id)],
            order='start_date desc', limit=1)
        return seasons and seasons[0] or False
