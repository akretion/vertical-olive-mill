# Copyright 2018-2023 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OliveOilProductionPack2Check(models.TransientModel):
    _name = 'olive.oil.production.pack2check'
    _description = 'Olive Oil Production Pack2check'
    _check_company_auto = True

    production_id = fields.Many2one(
        'olive.oil.production', string='Olive Oil Production', required=True)
    company_id = fields.Many2one(related='production_id.company_id')
    palox_ids = fields.Many2many(related='production_id.palox_ids')
    oil_product_id = fields.Many2one(related='production_id.oil_product_id')
    todo_arrival_line_ids = fields.Many2many(
        'olive.arrival.line', string='Arrival Lines Left to Process')
    arrival_line_id = fields.Many2one(
        'olive.arrival.line', string='Production Line',
        domain="[('production_id', '=', production_id)]",
        readonly=False, required=True, check_company=True)
    line_oil_ratio = fields.Float(related='arrival_line_id.oil_ratio')
    line_withdrawal_oil_qty = fields.Float(related='arrival_line_id.withdrawal_oil_qty')
    line_withdrawal_oil_qty_kg = fields.Float(
        related='arrival_line_id.withdrawal_oil_qty_kg')
    extra_ids = fields.One2many(related='arrival_line_id.extra_ids', readonly=False)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        assert self._context.get('active_model') == 'olive.oil.production'
        assert self._context.get('active_id')
        res['production_id'] = self._context['active_id']
        prod = self.env['olive.oil.production'].browse(res['production_id'])
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
        prod = self.production_id
        if self.todo_arrival_line_ids:
            new_line_id = self.todo_arrival_line_ids[0].id
            self.write({
                'arrival_line_id': new_line_id,
                'todo_arrival_line_ids': [(3, new_line_id)],
                })
            action = self.env['ir.actions.actions']._for_xml_id(
                'olive_mill.olive_oil_production_pack2check_action')
            action['res_id'] = self.id
            return action
        else:
            prod.pack2check()
