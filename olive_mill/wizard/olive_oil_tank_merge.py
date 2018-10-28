# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.tools import float_compare, float_is_zero, float_round
from odoo.exceptions import UserError
from datetime import datetime


class OliveOilTankMerge(models.TransientModel):
    _name = 'olive.oil.tank.merge'
    _description = 'Wizard to merge an olive oil tank'

    location_id = fields.Many2one(
        'stock.location', string='Olive Tank', required=True,
        domain=[('olive_tank_type', '!=', False)])

    def validate(self):
        self.ensure_one()
        pr_oil = self.env['decimal.precision'].precision_get('Olive Oil Volume')
        origin = _('Olive oil tank merge wizard')
        mpo = self.env['mrp.production']
        splo = self.env['stock.production.lot']
        sqo = self.env['stock.quant']
        loc = self.location_id
        qty = loc.olive_oil_tank_check(
            raise_if_empty=True, raise_if_reservation=True)
        quant_lot_rg = sqo.read_group(
                [('location_id', '=', loc.id)],
                ['qty', 'lot_id'], ['lot_id'])
        if len(quant_lot_rg) <= 1:
            raise UserError(_(
                "Oil tank '%s' is already merged.") % loc.name)
        product = loc.oil_product_id
        assert product.tracking == 'lot'
        assert product.olive_type == 'oil'
        boms = self.env['mrp.bom'].search([
            ('product_tmpl_id', '=', product.product_tmpl_id.id),
            ('type', '=', 'normal'),
            ('product_uom_id', '=', product.uom_id.id),
            ])
        bom = False
        for bom in boms:
            if (
                    len(bom.bom_line_ids) == 1 and
                    bom.bom_line_ids[0].product_id == product and
                    bom.bom_line_ids[0].product_uom_id == product.uom_id and
                    not float_compare(
                        bom.bom_line_ids[0].product_qty, bom.product_qty,
                        precision_digits=pr_oil)):
                break
        if not bom:
            raise UserError(_(
                "Could not find a bill of material for oil product '%s' to merge "
                "the oil tank.") % product.name)
        mo = mpo.create({
            'product_id': product.id,
            'product_qty': qty,
            'product_uom_id': product.uom_id.id,
            'location_src_id': loc.id,
            'location_dest_id': loc.id,
            'origin': origin,
            'bom_id': bom.id,
        })
        assert mo.state == 'confirmed'
        assert len(mo.move_raw_ids) == 1, 'Wrong raw moves'
        assert mo.move_raw_ids[0].product_id == product, 'Wrong product on raw move'
        assert len(mo.move_finished_ids) == 1, 'Wrong finished moves'
        assert mo.move_finished_ids[0].product_id == product, 'Wrong product on finished move'
        mo.action_assign()
        if mo.availability != 'assigned':
            raise UserError(_(
                "Could not reserve the oil to merge the tank %s. "
                "This should never happen.")
                % self.location_id.name)
        assert mo.move_raw_ids[0].move_lot_ids, 'No move_lot_ids'
        for move_lot in mo.move_raw_ids[0].move_lot_ids:
            assert move_lot.lot_id
            move_lot.quantity_done = move_lot.quantity
        # raw lines should be green at this step
        # Create finished lot
        merge_lot_name = self.env['ir.sequence'].next_by_code('olive.oil.merge.lot')
        new_lot = splo.create({
            'product_id': product.id,
            'name': merge_lot_name,
            })
        new_move_lots = self.env['stock.move.lots'].create({
            'move_id': mo.move_finished_ids[0].id,
            'product_id': product.id,
            'production_id': mo.id,
            'quantity': qty,
            'quantity_done': qty,
            'lot_id': new_lot.id,
            })
        for raw_move_lot in mo.move_raw_ids[0].move_lot_ids:
            assert not raw_move_lot.lot_produced_id
        mo.move_raw_ids[0].move_lot_ids.write({'lot_produced_id': new_lot.id})
        mo.write({
            'state': 'progress',
            'date_start': datetime.now(),
            })
        assert mo.post_visible == True
        mo.post_inventory()
        assert mo.check_to_done == True
        mo.button_mark_done()
        post_mo_qty = loc.olive_oil_tank_check(
            raise_if_reservation=True, raise_if_multi_lot=True)
        if float_compare(qty, post_mo_qty, precision_digits=pr_oil):
            raise (_(
                "In tank '%s', the oil quantity after the merge (%s) "
                "is different from the oil quantity before the merge (%s). "
                "This should never happen.") % (
                    loc.name, post_mo_qty, qty))
        action = self.env['ir.actions.act_window'].for_xml_id(
            'mrp', 'mrp_production_action')
        action.update({
            'res_id': mo.id,
            'views': False,
            'view_mode': 'form,tree,kanban,calendar',
            })
        return action
