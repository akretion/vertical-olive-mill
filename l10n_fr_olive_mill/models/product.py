# -*- coding: utf-8 -*-
# Copyright 2019 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    olive_oil_type = fields.Selection([
        ('virgin', 'Virgin'),
        ('extravirgin', 'Extra-Virgin'),
        ], string='Oil Type')
