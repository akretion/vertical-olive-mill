# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OrganicCertifyingEntity(models.Model):
    _name = 'organic.certifying.entity'
    _description = 'Organic Certifying Entity'
    _order = 'sequence'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)
    sequence = fields.Integer()
    active = fields.Boolean(default=True)

    _sql_constraints = [(
        'code_unique',
        'unique(code)',
        'This organic certifying entity code already exists.')]

    @api.depends('name', 'code')
    def name_get(self):
        res = []
        for entity in self:
            res.append((entity.id, '%s (%s)' % (entity.code, entity.name)))
        return res
