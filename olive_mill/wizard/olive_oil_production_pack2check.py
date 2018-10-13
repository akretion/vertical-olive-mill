# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
import odoo.addons.decimal_precision as dp
# from odoo.exceptions import UserError


class OliveOilProductionPack2Check(models.TransientModel):
    _name = 'olive.oil.production.pack2check'
    _description = 'Olive Oil Production pack2check'

    olive_oil_production_id = fields.Many2one(
        'olive.oil.production', string='Olive Oil Production', required=True)
    palox_id = fields.Many2one(
        related='olive_oil_production_id.palox_id', readonly=True)
    oil_product_id = fields.Many2one(
        related='olive_oil_production_id.oil_product_id', readonly=True)
    todo_arrival_line_ids = fields.Many2many(
        'olive.arrival.line', string='Arrival Lines Left to Process')
    arrival_line_id = fields.Many2one(
        'olive.arrival.line', required=True, string='Production Line')
    line_oil_qty = fields.Float(
        related='arrival_line_id.oil_qty', readonly=True)
    line_oil_ratio = fields.Float(
        related='arrival_line_id.oil_ratio', readonly=True)
    line_shrinkage_oil_qty = fields.Float(
        related='arrival_line_id.shrinkage_oil_qty', readonly=True)
    line_withdrawal_oil_qty = fields.Float(
        related='arrival_line_id.withdrawal_oil_qty', readonly=True)
    extra_ids = fields.One2many(
        'olive.oil.production.pack2check.line', 'wizard_id',
        string='Extra')

    @api.model
    def default_get(self, fields_list):
        res = super(OliveOilProductionPack2Check, self).default_get(
            fields_list)
        prod = self.env['olive.oil.production'].browse(
            res.get('olive_oil_production_id'))
        line_ids = [
            line.id for line in prod.line_ids
            if line.oil_destination in ('withdrawal', 'mix')]
        if line_ids:
            res['arrival_line_id'] = line_ids.pop(0)
        if line_ids:
            res['todo_arrival_line_ids'] = [(6, 0, line_ids)]
        return res

    def validate(self):
        self.ensure_one()
        prod = self.olive_oil_production_id
        line = self.arrival_line_id
        line.extra_ids.unlink()
        for extra in self.extra_ids:
            self.env['olive.arrival.line.extra'].create({
                'product_id': extra.product_id.id,
                'qty': extra.qty,
                'line_id': line.id,
                })
        print "self.todo_arrival_line_ids=", self.todo_arrival_line_ids
        if self.todo_arrival_line_ids:
            new_line_id = self.todo_arrival_line_ids[0].id
            self.write({
                'arrival_line_id': new_line_id,
                'todo_arrival_line_ids': [(3, new_line_id)],
                })
            self.extra_ids.unlink()
            action = self.env['ir.actions.act_window'].for_xml_id(
                'olive_mill', 'olive_oil_production_pack2check_action')
            action['res_id'] = self.id
            return action
        else:
            prod.pack2check()
            return True


class OliveOilProductionPack2CheckLine(models.TransientModel):
    _name = 'olive.oil.production.pack2check.line'
    _description = 'Equivalent of olive.arrival.line.extra in wizard'

    wizard_id = fields.Many2one(
        'olive.oil.production.pack2check',
        ondelete='cascade')
    product_id = fields.Many2one(
        'product.product', string='Extra Product',
        required=True, ondelete='restrict',
        domain=[
            ('olive_type', '=', 'bottle'),
            '|', ('tracking', '=', False), ('tracking', '=', 'none')])
    qty = fields.Float(
        string='Quantity', default=1,
        digits=dp.get_precision('Product Unit of Measure'), required=True)
    uom_id = fields.Many2one(
        related='product_id.uom_id', readonly=True)
