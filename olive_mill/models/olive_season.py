# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError, ValidationError


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

    _sql_constrains = [(
        'name_unique',
        'unique(name, company_id)',
        'This season name already exists in this company.')]

    @api.constrains('start_date', 'end_date')
    def season_check(self):
        for season in self:
            if season.end_date >= season.start_date:
                raise ValidationError(_(
                    "End Date must be after Start Date on season '%s'")
                    % season.name)
            oseasons = self.search([('end_date', '>', season.start_date)])
            if oseasons:
                raise ValidationError(_(
                    "Season '%s' (%s to %s) is after or over this season (%s)")
                    % (oseasons[0].name, oseasons[0].start_date,
                       oseasons[0].end_date, season.name))

    @api.model
    def get_current_season(self):
        today = fields.Date.context_today(self)
        seasons = self.search([
            ('start_date', '<=', today),
            ('end_date', '>=', today)])
        if seasons:
            return seasons[0]
        seasons = self.search(
            [('start_date', '<=', today)], order='start_date desc', limit=1)
        return seasons and seasons[0] or False
