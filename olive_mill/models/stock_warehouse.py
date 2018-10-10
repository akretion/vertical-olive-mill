# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import models, fields, api, _


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    olive_mill = fields.Boolean(string='Olive Mill')  # TODO add to view
    olive_shrinkage_loc_id = fields.Many2one(
        'stock.location', string='Olive Oil Shrinkage Tank',
        domain=[('olive_tank', '=', True)])
    olive_withdrawal_loc_id = fields.Many2one(
        'stock.location', string='Olive Oil Withdrawal Location',
        domain=[('olive_tank', '=', False), ('usage', '=', 'internal')])  # Could be move to pick type ?
#    olive_withdrawal_picking_type_id = fields.Many2one(
#        'stock.picking.type', string='Olive Oil Withdrawal Picking Type')
#    olive_sale_picking_type_id = fields.Many2one(
#        'stock.picking.type', string='Olive Oil Sale Picking Type')
    #olive_withdrawal_loc_id = fields.Many2one(  
    #    'stock.location', string='Oil Withdrawal Tank',
    #    domain=[('olive_tank', '=', True)])
