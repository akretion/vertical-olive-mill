# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.tools import float_compare, float_is_zero, float_round
from odoo.exceptions import UserError
from datetime import datetime


class OliveOilBottling(models.TransientModel):
    _name = 'olive.oil.bottling'
    _description = 'Wizard to fill-up olive oil bottles'

    bottle_product_id = fields.Many2one(
        'product.product', string='Oil Bottle to Produce',
        domain=[('olive_type', '=', 'bottle_full')], required=True,
        states={'produce': [('readonly', True)]})
    oil_product_id = fields.Many2one(
        'product.product', string='Oil Type', readonly=True)
    bom_id = fields.Many2one(
        'mrp.bom', string='Bill of Material', readonly=True)
    season_id = fields.Many2one(
        'olive.season', string='Season', required=True,
        default=lambda self: self.env['olive.season'].get_current_season(),
        states={'produce': [('readonly', True)]})
    quantity = fields.Integer(string='Qty of Bottles to Produce')
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse',
        domain=[('olive_mill', '=', True)],
        default=lambda self: self.env.user._default_olive_mill_wh(),
        states={'produce': [('readonly', True)]})
    src_location_id = fields.Many2one(
        'stock.location', string='Olive Tank',
        domain=[('olive_tank_type', '!=', False), ('usage', '=', 'internal')])
    other_src_location_id = fields.Many2one(
        'stock.location', string='Source Location for Empty Bottles',
        domain=[('usage', '=', 'internal')])
    dest_location_id = fields.Many2one(
        'stock.location', string='Destination Location for Full Bottles',
        domain=[('olive_tank_type', '=', False), ('usage', '=', 'internal')])
    expiry_date = fields.Date(string='Expiry Date')
    # TODO: also handle use of an existing lot ?
    lot_name = fields.Char(string='Lot')
    state = fields.Selection([
        ('select', 'Select Oil Bottle'),
        ('produce', 'Produce'),
        ], default='select', readonly=True, string='State')

    @api.onchange('season_id')
    def season_id_change(self):
        if self.season_id:
            self.expiry_date = self.season_id.default_expiry_date

    @api.onchange('warehouse_id')
    def warehouse_id_change(self):
        if self.warehouse_id:
            self.dest_location_id = self.warehouse_id.lot_stock_id
            self.other_src_location_id = self.warehouse_id.lot_stock_id

    def select2produce(self):
        self.ensure_one()
        bom, oil_product_id = self.bottle_product_id.oil_bottle_full_get_bom_and_oil_product()
        assert oil_product_id.olive_type == 'oil'
        self.write({
            'state': 'produce',
            'bom_id': bom.id,
            'oil_product_id': oil_product_id.id,
            })
        action = self.env.ref('olive_mill.olive_oil_bottling_action').read()[0]
        action['res_id'] = self.id
        return action

    def validate(self):
        self.ensure_one()
        assert self.state == 'produce'
        pr_oil = self.env['decimal.precision'].precision_get('Olive Oil Volume')
        origin = _('Olive oil bottling wizard')
        mpo = self.env['mrp.production']
        splo = self.env['stock.production.lot']
        sqo = self.env['stock.quant']
        smo = self.env['stock.move']
        oil_product = self.oil_product_id
        bottle_product = self.bottle_product_id
        bom = self.bom_id
        if self.quantity <= 0:
            raise UserError(_(
                "The quantity of bottles to produce must be positive."))
        assert self.src_location_id
        assert self.other_src_location_id
        assert self.dest_location_id
        assert self.expiry_date
        assert self.lot_name
        if self.expiry_date < fields.Date.context_today(self):
            raise UserError(_(
                "The expiry date should not be in the past."))
        qty = self.src_location_id.olive_oil_tank_check(
            raise_if_empty=True, raise_if_reservation=True,
            raise_if_multi_lot=True)
        assert oil_product.tracking == 'lot'
        assert bottle_product.tracking == 'lot'
        # TODO Check we have enogh oil qty ?
        # TODO also check for empty bottles ?
        mo = mpo.create({
            'product_id': bottle_product.id,
            'product_qty': self.quantity,
            'product_uom_id': bottle_product.uom_id.id,
            'location_src_id': self.src_location_id.id,
            'location_dest_id': self.dest_location_id.id,
            'origin': origin,
            'bom_id': bom.id,
        })
        assert mo.state == 'confirmed'
        assert len(mo.move_raw_ids) > 0, 'Missing raw moves'
        assert len(mo.move_finished_ids) == 1, 'Wrong finished moves'
        assert mo.move_finished_ids[0].product_id == bottle_product, 'Wrong product on finished move'
        oil_raw_move = smo.search([
            ('product_id.olive_type', '=', 'oil'),
            ('raw_material_production_id', '=', mo.id)])
        other_raw_moves = smo.search([
            ('product_id.olive_type', '!=', 'oil'),
            ('raw_material_production_id', '=', mo.id)])
        for rmove in other_raw_moves:
            if rmove.product_id.tracking in ('lot', 'serial'):
                raise UserError(_(
                    "The bill of material has the component '%s' "
                    "which is tracked by lot or serial. For the moment, "
                    "the only supported scenario is where the only component "
                    "of the bill of material tracked by lot is the oil.")
                    % rmove.product_id.display_name)
        # BOM has already been checked, so this should really never happen
        assert len(oil_raw_move) == 1, 'Wrong number of oil raw moves'
        # HACK change source location for other raw moves
        other_raw_moves.write({'location_id': self.other_src_location_id.id})
        mo.action_assign()
        if mo.availability != 'assigned':
            raise UserError(_(
                "Could not reserve the raw material for this bottling operation. "
                "Check that you have enough oil and empty bottles."))
        for move_lot in oil_raw_move.move_lot_ids:
            assert move_lot.lot_id
            move_lot.quantity_done = move_lot.quantity
        for rmove in other_raw_moves:
            rmove.quantity_done = rmove.product_uom_qty
        # raw lines should be green at this step
        # Create finished lot
        new_lot = splo.create({
            'product_id': bottle_product.id,
            'name': self.lot_name,
            'expiry_date': self.expiry_date,
            })
        new_move_lots = self.env['stock.move.lots'].create({
            'move_id': mo.move_finished_ids[0].id,
            'product_id': bottle_product.id,
            'production_id': mo.id,
            'quantity': self.quantity,
            'quantity_done': self.quantity,
            'lot_id': new_lot.id,
            })
        for raw_move_lot in oil_raw_move.move_lot_ids:
            assert not raw_move_lot.lot_produced_id
        oil_raw_move.move_lot_ids.write({'lot_produced_id': new_lot.id})
        mo.write({
            'state': 'progress',
            'date_start': datetime.now(),
            })
        assert mo.post_visible == True
        mo.post_inventory()
        assert mo.check_to_done == True
        mo.button_mark_done()
        action = self.env['ir.actions.act_window'].for_xml_id(
            'mrp', 'mrp_production_action')
        action.update({
            'res_id': mo.id,
            'views': False,
            'view_mode': 'form,tree,kanban,calendar',
            })
        return action
