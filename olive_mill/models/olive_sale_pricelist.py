# Copyright 2018-2023 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class OliveSalePricelist(models.Model):
    _name = 'olive.sale.pricelist'
    _description = 'Olive Sale Pricelist'
    _order = 'sequence'

    name = fields.Char(string='Pricelist Name', required=True)
    sequence = fields.Integer()
    company_id = fields.Many2one(
        'res.company', string='Company', ondelete='cascade', required=True,
        default=lambda self: self.env.company)
    active = fields.Boolean(default=True)
    line_ids = fields.One2many(
        'olive.sale.pricelist.line', 'pricelist_id', string='Lines')

    _sql_constraints = [(
        'name_unique',
        'unique(name)',
        'This profile already exists.')]

    def _prepare_speeddict(self):
        self.ensure_one()
        product2price = {}
        for line in self.line_ids:
            product2price[line.product_id] = line.price
        return product2price


class OliveSalePricelistLine(models.Model):
    _name = 'olive.sale.pricelist.line'
    _description = 'Olive Sale Pricelist Line'
    _order = 'pricelist_id'

    pricelist_id = fields.Many2one(
        'olive.sale.pricelist', ondelete='cascade', string='Olive Sale Pricelist')
    product_id = fields.Many2one(
        'product.product', string='Oil Product', required=True,
        domain=[('detailed_type', '=', 'olive_oil')])
    price = fields.Float(
        string='Price', digits='Product Price', required=True)
    currency_id = fields.Many2one(
        related='pricelist_id.company_id.currency_id', store=True)

    _sql_constraints = [(
        'pricelist_product_uniq',
        'unique(pricelist_id, product_id)',
        'There is already a line with the same product on this pricelist.')]
