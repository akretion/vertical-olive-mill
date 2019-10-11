# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    olive_operator = fields.Boolean(string='Olive Mill Operator')

    def _default_olive_mill_wh(self):
        self.ensure_one()
        wh = self.env['stock.warehouse'].search([
            ('company_id', '=', self.company_id.id),
            ('olive_mill', '=', True)],
            limit=1)
        return wh
