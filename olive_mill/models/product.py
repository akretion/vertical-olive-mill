# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    olive_type = fields.Selection([
        # Olives are not handled as products
        ('oil', 'Olive Oil'),
        ('bottle', 'Empty Oil Bottle'),
        ('bottle_full', 'Full Oil Bottle'),
        ('bottle_full_pack', 'Manufacture Pack of Full Oil Bottles'),
        ('bottle_full_pack_phantom', 'Kit Pack of Full Oil Bottles'),
        ('analysis', 'Analysis'),
        ('extra_service', 'Extra Service'),
        ('service', 'Production Service'),
        ('tax', 'Federation Tax'),
        ], string='Olive Type')
    olive_culture_type = fields.Selection([
        ('regular', 'Regular'),
        ('organic', 'Organic'),
        ('conversion', 'Conversion'),
        ], string='Culture Type')
    olive_bottle_free_full = fields.Boolean(
        string="Not Invoiced when Full")
    olive_invoice_service_ids = fields.Many2many(
        'product.product', 'product_template_olive_invoice_service_rel',
        'product_tmpl_id', 'product_id',
        string='Extra Production Services To Invoice',
        domain=[('olive_type', '=', 'service')])
    olive_analysis_uom = fields.Char(
        string='Unit of Measure of the Olive Oil Analysis')
    olive_analysis_decimal_precision = fields.Integer(
        string='Olive Oil Analysis Decimal Precision',
        default=1)
    olive_analysis_instrument = fields.Char(
        string='Instrument used for the Olive Oil Analysis')
    olive_analysis_precision = fields.Char(
        string='Precision of the Olive Oil Analysis')

    _sql_constraints = [(
        'olive_analysis_decimal_precision_positive',
        'CHECK(olive_analysis_decimal_precision >= 0)',
        'The decimal precision of the olive oil analysis must be positive.')]

    # DUPLICATED in product product
    @api.onchange('olive_type')
    def olive_type_change(self):
        liter_uom = self.env.ref('product.product_uom_litre')
        if self.olive_type == 'oil':
            if self.uom_id != liter_uom:
                self.uom_id = liter_uom
                self.uom_po_id = liter_uom
            self.tracking = 'lot'
        elif self.olive_type == 'bottle_full':
            self.tracking = 'lot'
        if self.olive_type in ('service', 'extra_service', 'tax'):
            self.type = 'service'
        elif self.olive_type == 'analysis':
            self.type == 'consu'
        if not self.olive_type:
            self.olive_culture_type = False

    @api.constrains('olive_type', 'uom_id', 'olive_culture_type', 'type')
    def check_olive_type(self):
        liter_uom = self.env.ref('product.product_uom_litre')
        unit_categ_uom = self.env.ref('product.product_uom_categ_unit')
        for pt in self:
            if pt.olive_type == 'oil':
                if not pt.olive_culture_type:
                    raise ValidationError(_(
                        "Product '%s' has an Olive Type 'Olive Oil', so a "
                        "culture type must also be configured.")
                        % pt.display_name)
                if pt.uom_id != liter_uom:
                    raise ValidationError(_(
                        "Product '%s' has an Olive Type 'Olive Oil' that "
                        "require 'Liter' as it's unit of measure "
                        "(current unit of measure is %s).")
                        % (pt.display_name, pt.uom_id.display_name))
                if pt.tracking != 'lot':
                    raise ValidationError(_(
                        "Product '%s' has an Olive Type 'Oil' that require "
                        "tracking by lots.") % pt.display_name)
            if pt.olive_type == 'bottle_full' and pt.tracking != 'lot':
                raise ValidationError(_(
                    "Product '%s' has an Olive Type 'Full Oil Bottle' "
                    "that require tracking by lots.") % pt.display_name)
            if (
                    pt.olive_type in ('bottle', 'bottle_full', 'analysis') and
                    pt.uom_id.category_id != unit_categ_uom):
                raise ValidationError(_(
                    "Product '%s' has an Olive Type 'Bottle' or 'Analysis' "
                    "that require a unit of measure that belong to the "
                    "'Unit' category (current unit of measure: %s).")
                    % (pt.display_name, pt.uom_id.display_name))
            if pt.olive_type == 'analysis' and pt.type != 'consu':
                raise ValidationError(_(
                    "Product '%s' has an Olive Type 'Analysis', so "
                    "it must be configured as a consumable.")
                    % pt.display_name)
            if (
                    pt.olive_type in ('service', 'extra_service', 'tax') and
                    pt.type != 'service'):
                raise ValidationError(_(
                    "Product '%s' has an Olive Type 'Production Service', "
                    "'Extra Service' or 'Federation Tax', so it must be "
                    "configured as a Service.") % (
                        pt.display_name))


class ProductProduct(models.Model):
    _inherit = 'product.product'

    shrinkage_prodlot_id = fields.Many2one(
        'stock.production.lot', string='Shrinkage Production Lot',
        copy=False,
        help="Select the generic production lot that will be used for all "
        "moves of this olive oil product to the shrinkage tank.")

    # DUPLICATED in product template
    @api.onchange('olive_type')
    def olive_type_change(self):
        liter_uom = self.env.ref('product.product_uom_litre')
        if self.olive_type == 'oil':
            if self.uom_id != liter_uom:
                self.uom_id = liter_uom
                self.uom_po_id = liter_uom
            self.tracking = 'lot'
        elif self.olive_type == 'bottle_full':
            self.tracking = 'lot'
        if self.olive_type in ('service', 'extra_service'):
            self.type = 'service'
        elif self.olive_type == 'analysis':
            self.type == 'consu'
        if not self.olive_type:
            self.olive_culture_type = False

    def olive_create_merge_bom(self):
        mbo = self.env['mrp.bom']
        for product in self.filtered(lambda p: p.olive_type == 'oil'):
            mbo.create({
                'product_id': product.id,
                'product_tmpl_id': product.product_tmpl_id.id,
                'product_uom_id': product.uom_id.id,
                'product_qty': 1,
                'ready_to_produce': 'all_available',
                'bom_line_ids': [(0, 0, {
                    'product_id': product.id,
                    'product_uom_id': product.uom_id.id,
                    'product_qty': 1,
                    })],
                })

    def oil_bottle_full_get_bom_and_oil_product(self):
        self.ensure_one()
        assert self.olive_type == 'bottle_full'
        boms = self.env['mrp.bom'].search([
            ('product_tmpl_id', '=', self.product_tmpl_id.id),
            ('type', '=', 'normal'),
            ('product_uom_id', '=', self.uom_id.id),
            ])
        if not boms:
            raise UserError(_(
                "No bill of material for product '%s'.") % self.display_name)
        if len(boms) > 1:
            raise UserError(_(
                "There are several bill of materials for product '%s'. "
                "This scenario is not supported.") % self.display_name)
        bom = boms[0]
        oil_bom_lines = self.env['mrp.bom.line'].search([
            ('product_id.olive_type', '=', 'oil'), ('bom_id', '=', bom.id)])
        if not oil_bom_lines:
            raise UserError(_(
                "The bill of material '%s' (ID %d) doesn't have any "
                "line with an oil product.") % (bom.display_name, bom.id))
        if len(oil_bom_lines) > 1:
            raise UserError(_(
                "The bill of material '%s' (ID %d) has several lines "
                "with an oil product. This scenario is not supported for "
                "the moment.") % (bom.display_name, bom.id))
        oil_bom_line = oil_bom_lines[0]
        liter_uom = self.env.ref('product.product_uom_litre')
        if oil_bom_line.product_uom_id != liter_uom:
            raise UserError(_(
                "The component line with product '%s' of the "
                "bill of material '%s' (ID %d) should have "
                "liters as the unit of measure.") % (
                    oil_bom_line.product_id.display_name,
                    bom.display_name, bom.id))
        volume = oil_bom_line.product_qty
        prec = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')
        if float_compare(volume, 0, precision_digits=prec) <= 0:
            raise UserError(_(
                "The oil volume (%s) can't negative on bill of "
                "material '%s' (ID %d).") % (
                    volume, bom.display_name, bom.id))
        return (bom, oil_bom_lines[0].product_id, volume)

    def oil_bottle_full_pack_get_bottles(self):
        self.ensure_one()
        assert self.olive_type == 'bottle_full_pack'
        boms = self.env['mrp.bom'].search([
            ('product_tmpl_id', '=', self.product_tmpl_id.id),
            ('type', '=', 'normal'),
            ('product_uom_id', '=', self.uom_id.id),
            ])
        if not boms:
            raise UserError(_(
                "No bill of material with type 'Manufacture this product' "
                "for product '%s'.") % self.display_name)
        if len(boms) > 1:
            raise UserError(_(
                "There are several bill of materials for product '%s'. "
                "This scenario is not supported.") % self.display_name)
        bom = boms[0]
        full_bottle_lines = self.env['mrp.bom.line'].search([
            ('product_id.olive_type', '=', 'bottle_full'), ('bom_id', '=', bom.id)])
        if not full_bottle_lines:
            raise UserError(_(
                "The bill of material '%s' (ID %d) doesn't have any "
                "line with a full oil bottle.") % (bom.display_name, bom.id))
        res = {}
        for full_bottle_line in full_bottle_lines:
            if full_bottle_line.product_id in res:
                res[full_bottle_line.product_id] += full_bottle_line.product_qty
            else:
                res[full_bottle_line.product_id] = full_bottle_line.product_qty
        return res
