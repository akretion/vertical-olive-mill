# Copyright 2018-2023 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    olive_mill = fields.Boolean(string='Olive Mill')
    olive_regular_case_total = fields.Integer(string='Regular Cases Total')
    olive_regular_case_stock = fields.Integer(
        compute='_compute_cases', string='Regular Cases in Stock')
    olive_organic_case_total = fields.Integer(string='Organic Cases Total')
    olive_organic_case_stock = fields.Integer(
        compute='_compute_cases', string='Organic Cases in Stock')
    olive_withdrawal_loc_id = fields.Many2one(
        'stock.location', string='Olive Oil Withdrawal Location', check_company=True,
        domain=[('olive_tank_type', '=', False), ('usage', '=', 'internal')])

    @api.depends('olive_organic_case_total', 'olive_regular_case_total')
    def _compute_cases(self):
        cases_res = self.env['olive.lended.case'].read_group(
            [('warehouse_id', 'in', self.ids)],
            ['warehouse_id', 'regular_qty', 'organic_qty'], ['warehouse_id'])
        if cases_res:
            for cases_re in cases_res:
                wh = self.browse(cases_re['warehouse_id'][0])
                wh.olive_regular_case_stock =\
                    wh.olive_regular_case_total - cases_re['regular_qty']
                wh.olive_organic_case_stock =\
                    wh.olive_organic_case_total - cases_re['organic_qty']
        else:
            for wh in self:
                wh.olive_regular_case_stock = wh.olive_regular_case_total
                wh.olive_organic_case_stock = wh.olive_organic_case_total

    def olive_get_shrinkage_tank(self, oil_product, raise_if_not_found=True):
        self.ensure_one()
        assert oil_product, 'oil_product is a required arg'
        sloc = self.env['stock.location'].search([
            ('olive_tank_type', '=', 'shrinkage'),
            ('id', 'child_of', self.view_location_id.id),
            ('olive_shrinkage_oil_product_ids', '=', oil_product.id)],
            limit=1)
        if not sloc and raise_if_not_found:
            raise UserError(_(
                "Could not find a shrinkage tank in warehouse '%s' "
                "that accepts '%s'.") % (
                    self.display_name, oil_product.name))
        return sloc or False
