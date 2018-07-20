# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    olive_type = fields.Selection([
        ('olive', 'Olive'),
        ('oil', 'Olive Oil'),
        ('bottle', 'Oil Bottle'),
        ], string='Olive Type')
    olive_culture_type = fields.Selection([
        ('regular', 'Regular'),
        ('organic', 'Organic'),
        ('conversion', 'Conversion'),
        ], string='culture Type')

    @api.onchange('olive_type')
    def olive_type_change(self):
        kg_uom = self.env.ref('product.product_uom_kgm')
        if self.olive_type in ('olive', 'oil') and self.uom_id != kg_uom:
            self.uom_id = kg_uom
            self.uom_po_id = kg_uom
        if not self.olive_type:
            self.olive_culture_type = False

    @api.constrains('olive_type', 'uom_id', 'olive_culture_type')
    def check_olive_type(self):
        kg_uom = self.env.ref('product.product_uom_kgm')
        unit_categ_uom = self.env.ref('product.product_uom_categ_unit')
        for pt in self:
            if pt.olive_type and not pt.olive_culture_type:
                raise ValidationError(_(
                    "Product '%s' has an Olive Type, so a culture Type "
                    "must also be configured.") % pt.display_name)
            if pt.olive_type in ('olive', 'oil') and pt.uom_id != kg_uom:
                raise ValidationError(_(
                    "Product '%s' has an Olive Type (%s) that require 'Kg' "
                    "as it's unit of measure (current unit of measure is %s)")
                    % (pt.display_name, pt.olive_type, pt.uom_id.display_name))
            if (
                    pt.olive_type == 'bottle' and
                    pt.uom_id.category_id != unit_categ_uom):
                raise ValidationError(_(
                    "Product '%s' has an Olive Type 'Bottle' that require a "
                    "unit of measure that belong to the 'Unit' category "
                    "(current unit of measure: %s).")
                    % (pt.display_name, pt.uom_id.display_name))
