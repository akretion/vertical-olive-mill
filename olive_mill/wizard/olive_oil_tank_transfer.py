# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, _
import odoo.addons.decimal_precision as dp


class OliveOilTankTransfer(models.TransientModel):
    _name = 'olive.oil.tank.transfer'
    _description = 'Wizard for olive oil tank transfer'

    src_location_id = fields.Many2one(
        'stock.location', string='Source Olive Tank', required=True)
    dest_location_id = fields.Many2one(
        'stock.location', string='Destination Olive Tank', required=True)
    transfer_type = fields.Selection([
        ('full', 'Full Transfer'),
        ('partial', 'Partial Transfer'),
        ], default='partial', required=True, string='Transfer Type')
    quantity = fields.Float(
        string='Oil Quantity to Transfer (L)',
        digits=dp.get_precision('Olive Oil Volume'))
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse', required=True,
        domain=[('olive_mill', '=', True)],
        default=lambda self: self.env.user._default_olive_mill_wh())

    def validate(self):
        self.ensure_one()
        origin = _('Olive oil tank transfer wizard')
        partial_transfer_qty = False
        if self.transfer_type == 'partial':
            partial_transfer_qty = self.quantity
        pick = self.src_location_id.olive_oil_transfer(
            self.dest_location_id, self.transfer_type, self.warehouse_id,
            origin=origin, partial_transfer_qty=partial_transfer_qty,
            auto_validate=True)
        action = self.env['ir.actions.act_window'].for_xml_id(
            'stock', 'action_picking_tree_all')
        action.update({
            'res_id': pick.id,
            'views': False,
            'view_mode': 'form,tree,kanban,calendar',
            })
        return action
