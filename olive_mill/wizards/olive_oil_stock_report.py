# Copyright 2024 Akretion France (https://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.tools import float_is_zero


class OliveOilStockReport(models.TransientModel):
    _name = 'olive.oil.stock.report'
    _description = 'Wizard to show current stock of olive oil'

    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    location_ids = fields.Many2many(
        'stock.location', string="Filter by Location",
        domain="[('company_id', '=', company_id), ('usage', 'in', ('internal', 'view', 'transit'))]",
        help="If empty, the stock will be shown for all the internal and transit locations of the selected company.")
    line_ids = fields.One2many('olive.oil.stock.report.line', 'parent_id', string='Stock Lines', readonly=True, compute='_compute_line_ids')

    @api.depends('company_id', 'location_ids')
    def _compute_line_ids(self):
        sqo = self.env['stock.quant']
        ppo = self.env['product.product']
        slo = self.env['stock.location']
        prec = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        bottle2oilandvolume = ppo._get_bottle2oilandvolume()
        # bottle2oilandvolume is for bottles and manufactured pack of bottles
        # {bottle1_id: {oil_product1_id: 0.75, oil_product2_id: 0.75}}
        for wiz in self:
            odoo_res = [(5, )]
            if wiz.company_id:
                oilproduct2qtydict = {}
                loc_base_domain = [
                    ('company_id', '=', wiz.company_id.id),
                    ('usage', 'in', ('internal', 'transit')),
                    ]
                if wiz.location_ids:
                    location_ids = slo.search(loc_base_domain + [('id', 'child_of', wiz.location_ids.ids)]).ids
                else:
                    location_ids = slo.search(loc_base_domain).ids
                oil_products = ppo.with_context(active_test=False).search([('detailed_type', '=', 'olive_oil')])
                for oil_product in oil_products:
                    oilproduct2qtydict[oil_product.id] = {'loose_qty': 0.0, 'in_bottle_qty': 0.0}

                # Loose oil
                quant_base_domain = [
                    ('company_id', '=', wiz.company_id.id),
                    ('location_id', 'in', location_ids),
                    ('owner_id', '=', False),
                    ]
                rg_res = sqo.read_group(
                    quant_base_domain + [('product_id', 'in', oil_products.ids)],
                    ['product_id', 'quantity:sum'],
                    ['product_id'])
                for rg_re in rg_res:
                    oilproduct2qtydict[rg_re['product_id'][0]]['loose_qty'] = rg_re['quantity']

                # Bottles
                rg_res = sqo.read_group(
                    quant_base_domain + [('product_id', 'in', list(bottle2oilandvolume))],
                    ['product_id', 'quantity:sum'],
                    ['product_id'])
                for rg_re in rg_res:
                    product_id = rg_re['product_id'][0]
                    product_qty = rg_re['quantity']
                    for oil_product_id, volume in bottle2oilandvolume[product_id].items():
                        oil_qty = product_qty * volume
                        oilproduct2qtydict[oil_product_id]['in_bottle_qty'] += oil_qty

                # total and filter 0 qty
                for oil_product_id, qty_dict in oilproduct2qtydict.items():
                    if (
                            not float_is_zero(qty_dict['loose_qty'], precision_digits=prec) or
                            not float_is_zero(qty_dict['in_bottle_qty'], precision_digits=prec)):
                        total_qty = qty_dict['loose_qty'] + qty_dict['in_bottle_qty']
                        create_dict = dict(qty_dict, oil_product_id=oil_product_id, total_qty=total_qty)
                        odoo_res.append((0, 0, create_dict))

            wiz.line_ids = odoo_res


class OliveOilStockReportLine(models.TransientModel):
    _name = 'olive.oil.stock.report.line'
    _description = 'Wizard line to show current stock of olive oil'

    parent_id = fields.Many2one('olive.oil.stock.report', ondelete='cascade')
    oil_product_id = fields.Many2one('product.product', string='Olive Oil', readonly=True, required=True)
    loose_qty = fields.Float(
        string='Loose Qty (L)', digits='Product Unit of Measure', readonly=True)
    in_bottle_qty = fields.Float(
        string='In Bottle Qty (L)', digits='Product Unit of Measure', readonly=True)
    total_qty = fields.Float(
        string='Total Qty (L)', digits='Product Unit of Measure', readonly=True)
