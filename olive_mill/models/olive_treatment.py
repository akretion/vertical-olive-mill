# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class OliveTreatment(models.Model):
    _name = 'olive.treatment'
    _description = 'Olive Treatment'

    name = fields.Char(string='Name', required=True)

    _sql_constraints = [(
        'name_unique',
        'unique(name)',
        'This treatment product already exists.')]
