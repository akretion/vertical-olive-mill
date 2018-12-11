# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api, _
from odoo.exceptions import UserError


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    def olive_out_invoice_price_update(self):
        self.ensure_one()
        oalines = self.env['olive.arrival.line'].search([
            ('out_invoice_id', '=', self.id),
            ('oil_destination', 'in', ('sale', 'mix'))])
        if oalines:
            oproducts = self.env['product.product'].search([
                ('olive_type', '=', 'service')])
            production_service = self.company_id.olive_oil_production_product_id
            total_amount = 0.0
            total_qty = 0.0
            kg_uom = self.env.ref('product.product_uom_kgm')
            for iline in self.invoice_line_ids:
                if iline.product_id in oproducts:
                    total_amount += iline.price_subtotal_signed
                if iline.product_id == production_service:
                    total_qty += iline.quantity
                    if iline.uom_id != kg_uom:
                        raise UserError(_(
                            "Invoice line '%s' has a production "
                            "product so it's unit of measure "
                            "should be kg.") % iline.name)
            unit_price_per_kg = 0.0
            if total_qty:
                unit_price_per_kg = total_amount / total_qty
            for oaline in oalines:
                unit_price_per_liter = 0.0
                if oaline.oil_ratio_net:
                    unit_price_per_liter = unit_price_per_kg * 100 / oaline.oil_ratio_net
                oil_service_sale_price_total = unit_price_per_liter * oaline.sale_oil_qty
                oil_service_sale_price_unit = unit_price_per_liter
                oaline.write({
                    'oil_service_sale_price_unit': oil_service_sale_price_unit,
                    'oil_service_sale_price_total': oil_service_sale_price_total,
                    })

    def olive_in_invoice_price_update(self):
        self.ensure_one()
        liter_uom = self.env.ref('product.product_uom_litre')
        for iline in self.invoice_line_ids:
            oalines = self.env['olive.arrival.line'].search([
                ('in_invoice_line_id', '=', iline.id),
                ('oil_destination', 'in', ('sale', 'mix'))])
            if oalines:
                # price_subtotal_signed is in company cur
                if iline.uom_id != liter_uom:
                    raise UserError(_(
                        "Invoice Line '%s' has an olive oil product so it "
                        "should have liter as unit of measure.") % iline.name)
                oil_sale_price_unit = 0.0
                if iline.quantity:
                    oil_sale_price_unit = iline.price_subtotal_signed / iline.quantity
                for oaline in oalines:
                    oaline.write({
                        'oil_sale_price_unit': oil_sale_price_unit,
                        'oil_sale_price_total': oil_sale_price_unit * oaline.sale_oil_qty,
                        })

    @api.multi
    def action_move_create(self):
        for invoice in self:
            if invoice.partner_id.olive_farmer:  # just for perf
                if invoice.type == 'out_invoice':
                    invoice.olive_out_invoice_price_update()
                elif invoice.type == 'in_invoice':
                    invoice.olive_in_invoice_price_update()
        return super(AccountInvoice, self).action_move_create()
