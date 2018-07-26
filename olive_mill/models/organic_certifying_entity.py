# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class OrganicCertifyingEntity(models.Model):
    _name = 'organic.certifying.entity'
    _description = 'Organic Certifying Entity'
    _order = 'sequence'

    name = fields.Char(string='Name', required=True)
    sequence = fields.Integer()
    active = fields.Boolean(default=True)

    _sql_constraints = [(
        'name_unique',
        'unique(name)',
        'This organic certifying entity already exists.')]
