# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, _
from odoo.tools import float_compare
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
        ppo = self.env['product.product']
        mpo = self.env['mrp.production']
        splo = self.env['stock.production.lot']
        sqo = self.env['stock.quant']
        loc = self.location_id
        qty = loc.olive_oil_tank_check(raise_if_not_merged=False)
        # Check if already merged
        error_msg = _(
            "Oil tank '%s' is already merged.") % loc.name
        quant_lot_rg = sqo.read_group(
            [('location_id', '=', loc.id)],
            ['qty', 'lot_id'], ['lot_id'])
        if self.location_id.olive_tank_type == 'risouletto':
            if len(quant_lot_rg) == 1:
                lot = splo.browse(quant_lot_rg[0]['lot_id'][0])
                if lot.product_id == loc.oil_product_id:
                    raise UserError(error_msg)
        else:
            if len(quant_lot_rg) == 1:
                raise UserError(error_msg)
        product = loc.oil_product_id
        assert product.tracking == 'lot'
        assert product.olive_type == 'oil'
        boms = self.env['mrp.bom'].search([
            ('product_tmpl_id', '=', product.product_tmpl_id.id),
            ('type', '=', 'normal'),
            ('product_uom_id', '=', product.uom_id.id),
            ])
        if len(boms) != 1:
            raise UserError(_(
                "The oil product '%s' should only have a single bill "
                "of material.") % product.display_name)
        liter_uom = self.env.ref('product.product_uom_litre')
        bom = boms[0]
        if bom.product_uom_id != liter_uom:
            raise UserError(_(
                "The unit of measure of the bill of material of product "
                "'%s' should be liters.") % product.display_name)
        bom_lines_qty = 0.0
        for bom_line in bom.bom_line_ids:
            if bom_line.product_id.olive_type != 'oil':
                raise UserError(_(
                    "The bill of material of the oil product '%s' "
                    "should only have oil components.")
                    % product.display_name)
            if bom_line.product_uom_id != liter_uom:
                raise UserError(_(
                    "On the bill of material of product '%s', the line with "
                    "product '%s' should have liters as unit of measure.") % (
                        product.display_name, bom_line.product_id.display_name))
            bom_lines_qty += bom_line.product_qty
        p_prec = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        if float_compare(bom_lines_qty, bom.product_qty, precision_digits=p_prec):
            raise UserError(_(
                "The bill of material of the oil product '%s' is wrong: "
                "the sum of the quantity of lines (%s) should be the quantity "
                "of the bill of material (%s).")
                % (product.display_name, bom_lines_qty, bom.product_qty))
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
        if loc.olive_tank_type != 'risouletto':
            if len(mo.move_raw_ids) != 1:
                raise UserError(_(
                    "Wrong bill of material for olive product '%s' "
                    "configured on oil tank '%s': it should have a single "
                    "component and this component should be the same product.")
                    % (product.display_name, loc.name))
            if mo.move_raw_ids[0].product_id != product:
                raise UserError(_(
                    "Wrong bill of material for olive product '%s' "
                    "configured on oil tank '%s': it's single component "
                    "should be the same product.") % (
                        product.display_name, loc.name))
        else:
            # Write qty on raw moves
            productid2rawmoves = {}
            for rmove in mo.move_raw_ids:
                assert rmove.product_id not in productid2rawmoves, 'Double product in raw moves'
                productid2rawmoves[rmove.product_id.id] = rmove
            quant_rg = sqo.read_group(
                [('location_id', '=', loc.id)],
                ['qty', 'product_id'], ['product_id'])
            for qrg in quant_rg:
                ris_tank_product_id = qrg['product_id'][0]
                if ris_tank_product_id not in productid2rawmoves:
                    ris_tank_product = ppo.browse(ris_tank_product_id)
                    raise UserError(_(
                        "Product '%s' is not present on the bill of material "
                        "of product '%s'.") % (ris_tank_product.display_name, product.display_name))
                raw_move = productid2rawmoves[ris_tank_product_id]
                raw_move.product_uom_qty = qrg['qty']
                productid2rawmoves.pop(ris_tank_product_id)
            for empty_raw_move in productid2rawmoves.values():
                empty_raw_move.product_uom_qty = 0
                empty_raw_move.action_cancel()

        assert len(mo.move_finished_ids) == 1, 'Wrong finished moves'
        assert mo.move_finished_ids[0].product_id == product, 'Wrong product on finished move'
        mo.action_assign()
        if mo.availability != 'assigned':
            raise UserError(_(
                "Could not reserve the oil to merge the tank %s. "
                "This should never happen.")
                % self.location_id.name)
        for raw_move in mo.move_raw_ids.filtered(lambda r: r.state != 'cancel'):
            assert raw_move.move_lot_ids, 'No move_lot_ids'
            for move_lot in raw_move.move_lot_ids:
                assert move_lot.lot_id
                move_lot.quantity_done = move_lot.quantity
        # raw lines should be green at this step
        # Create finished lot
        merge_lot_name = self.env['ir.sequence'].next_by_code('olive.oil.merge.lot')
        new_lot = splo.create({
            'product_id': product.id,
            'name': merge_lot_name,
            })
        self.env['stock.move.lots'].create({
            'move_id': mo.move_finished_ids[0].id,
            'product_id': product.id,
            'production_id': mo.id,
            'quantity': qty,
            'quantity_done': qty,
            'lot_id': new_lot.id,
            })
        for raw_move in mo.move_raw_ids.filtered(lambda r: r.state != 'cancel'):
            for raw_move_lot in raw_move.move_lot_ids:
                assert not raw_move_lot.lot_produced_id
            raw_move.move_lot_ids.write({'lot_produced_id': new_lot.id})
        mo.write({
            'state': 'progress',
            'date_start': datetime.now(),
            })
        assert mo.post_visible is True
        mo.post_inventory()
        assert mo.check_to_done is True
        mo.button_mark_done()
        post_mo_qty = loc.olive_oil_tank_check()
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
