# Copyright 2018-2023 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import api, models


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    # to merge a tank, we use a bom with olive oil product as finished product AND as single component
    # bom_id is NOT required on mrp.production, so we could try to avoid using them in v14
    @api.constrains('product_id', 'product_tmpl_id', 'bom_line_ids')
    def _check_product_recursion(self):
        for bom in self.filtered(lambda b: b.product_tmpl_id.olive_type != 'oil'):
            super(MrpBom, bom)._check_product_recursion()
