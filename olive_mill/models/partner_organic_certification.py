# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class PartnerOrganicCertification(models.Model):
    _name = 'partner.organic.certification'
    _description = 'Farmer Organic Certification'
    _order = 'season_id desc'

    partner_id = fields.Many2one(
        'res.partner', string='Farmer', ondelete='cascade',
        domain=[('parent_id', '=', False), ('olive_farmer', '=', True)],
        states={'done': [('readonly', True)]})
    season_id = fields.Many2one(
        'olive.season', string='Season', required=True,
        default=lambda self: self.env['olive.season'].get_current_season(),
        states={'done': [('readonly', True)]})
    company_id = fields.Many2one(
        related='season_id.company_id', store=True, readonly=True, string='Company',
        compute_sudo=True)
    certifying_entity_id = fields.Many2one(
        'organic.certifying.entity', string='Certifying Entity', required=True,
        ondelete='restrict', states={'done': [('readonly', True)]},
        help="Default value: same as previous season.")
    conversion = fields.Boolean(
        string='Conversion', states={'done': [('readonly', True)]})
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Valid'),
        ], string='State', default='draft', copy=False, readonly=True)
    validation_user_id = fields.Many2one(
        'res.users', string='Validated by', ondelete='restrict', readonly=True)
    validation_datetime = fields.Datetime(string='Validated on', readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super(PartnerOrganicCertification, self).default_get(fields_list)
        if self._context.get('default_partner_id'):
            previous_cert = self.search([
                ('partner_id', '=', self._context['default_partner_id']),
                ('state', '=', 'done'),
                ], order='season_id desc', limit=1)
            if previous_cert:
                res['certifying_entity_id'] = previous_cert.certifying_entity_id.id
                res['conversion'] = previous_cert.conversion
        return res

    def validate(self):
        self.ensure_one()
        self.write({
            'state': 'done',
            'validation_user_id': self.env.user.id,
            'validation_datetime': fields.Datetime.now(),
            })

    _sql_constraints = [(
        'partner_season_unique',
        'unique(season_id, partner_id)',
        'This farmer already has a certification for that season.')]
