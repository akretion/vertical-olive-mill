# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero, float_round
import odoo.addons.decimal_precision as dp


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    @api.constrains('product_id', 'product_tmpl_id', 'bom_line_ids')
    def _check_product_recursion(self):
        for bom in self.filtered(lambda b: b.product_id.olive_type != 'oil'):
            super(MrpBom, bom)._check_product_recursion()
