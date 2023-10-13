# Copyright 2018-2023 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, _


class OliveOilTankTransfer(models.TransientModel):
    _name = 'olive.oil.tank.transfer'
    _description = 'Wizard for olive oil tank transfer'
    _check_company_auto = True

    company_id = fields.Many2one(
        'res.company', ondelete='cascade', required=True,
        default=lambda self: self.env.company)
    src_location_id = fields.Many2one(
        'stock.location', string='Source Olive Tank', required=True, check_company=True,
        domain="[('company_id', '=', company_id), ('olive_tank_type', '!=', False)]")
    dest_location_id = fields.Many2one(
        'stock.location', string='Destination Olive Tank', required=True, check_company=True,
        domain="[('company_id', '=', company_id), ('olive_tank_type', '!=', False)]")
    transfer_type = fields.Selection([
        ('full', 'Full Transfer'),
        ('partial', 'Partial Transfer'),
        ], default='partial', required=True, string='Transfer Type')
    quantity = fields.Float(
        string='Oil Quantity to Transfer (L)',
        digits='Olive Oil Volume')
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse', required=True, check_company=True,
        domain="[('olive_mill', '=', True), ('company_id', '=', company_id)]",
        default=lambda self: self.env.user._default_olive_mill_wh())

    def validate(self):
        self.ensure_one()
        origin = _('Olive oil tank transfer wizard')
        partial_transfer_qty = False
        if self.transfer_type == 'partial':
            partial_transfer_qty = self.quantity
        pick = self.src_location_id.olive_oil_transfer(
            self.dest_location_id, self.transfer_type, self.warehouse_id,
            origin=origin, partial_transfer_qty=partial_transfer_qty)
        action = self.env['ir.actions.actions']._for_xml_id('stock.action_picking_tree_all')
        action.update({
            'res_id': pick.id,
            'views': False,
            'view_mode': 'form,tree,kanban,calendar',
            })
        return action
