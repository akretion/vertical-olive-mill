# Copyright 2024 Akretion France (https://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ProtectedGeoIndication(models.Model):
    _name = 'protected.geo.indication'
    _description = 'Protected Geographical Indication'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    company_id = fields.Many2one('res.company', required=False)
    tax_product_id = fields.Many2one(
        'product.product', domain=[('detailed_type', '=', 'olive_tax')],
        ondelete='restrict')
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    ochard_count = fields.Integer(compute="_compute_ochard_count")
    product_template_count = fields.Integer(compute="_compute_product_template_count")

    _sql_constraints = [(
        'name_company_unique',
        'unique(name, company_id)',
        'This protected geographical indication already exists.')]

    def _compute_ochard_count(self):
        rg_res = self.env['olive.ochard'].read_group(
            [('geo_id', 'in', self.ids)],
            ['geo_id'], ['geo_id'])
        mapped_data = dict(
            [(x['geo_id'][0], x['geo_id_count']) for x in rg_res])
        for geo in self:
            geo.ochard_count = mapped_data.get(geo.id, 0)

    def _compute_product_template_count(self):
        rg_res = self.env['product.template'].read_group(
            [('olive_geo_id', 'in', self.ids), ('detailed_type', '=like', 'olive_%')],
            ['olive_geo_id'], ['olive_geo_id'])
        mapped_data = dict(
            [(x['olive_geo_id'][0], x['olive_geo_id_count']) for x in rg_res])
        for geo in self:
            geo.product_template_count = mapped_data.get(geo.id, 0)
