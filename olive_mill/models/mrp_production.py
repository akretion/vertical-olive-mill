# -*- coding: utf-8 -*-
# © 2017 Barroux Abbey (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    green = fields.Boolean(string='Green')

    def stock_move_lots_copy_todo2done(self):
        self.ensure_one()
        for raw_move in self.move_raw_ids:
            if raw_move.product_id.tracking in ('lot', 'serial'):
                for move_lot in raw_move.active_move_lot_ids:
                    if move_lot.lot_id:
                        move_lot.quantity_done = move_lot.quantity
        self.green = True
        return True

    @api.multi
    def action_assign(self):
        sqo = self.env['stock.quant']
        for production in self:
            if production.product_id.oil_product_type == 'can':
                for raw_move in production.move_raw_ids:
                    if raw_move.product_id.oil_product_type in ('oil', 'olive'):
                        quants = sqo.search([('location_id', '=', raw_move.location_id.id), ('product_id', '=', raw_move.product_id.id)])
                        lots = []
                        for quant in quants:
                            if quant.lot_id and quant.lot_id.id not in lots:
                                lots.append(quant.lot_id.id)
                        if len(lots) > 1:
                            raise UserError(_(
                                "You cannot consume '%s' from severals different lots on '%s'. You need to merge them first.") % (raw_move.product_id.display_name, raw_move.location_id.display_name))
        return super(MrpProduction, self).action_assign()
