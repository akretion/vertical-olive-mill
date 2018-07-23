# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import models, fields, api, _
from odoo.exceptions import UserError


class OliveConfigSettings(models.TransientModel):
    _name = 'olive.config.settings'
    _inherit = 'res.config.settings'

    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.user.company_id, required=True)
    olive_qty_per_palox = fields.Integer(
        related='company_id.olive_qty_per_palox')
