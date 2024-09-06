# Copyright 2018-2024 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class OliveOilProductionProductSwap(models.TransientModel):
    _name = 'olive.oil.production.product.swap'
    _description = 'Swap oil type on olive oil production'
    _check_company_auto = True

    production_id = fields.Many2one(
        'olive.oil.production', string='Olive Oil Production', required=True)
    company_id = fields.Many2one(related='production_id.company_id')
    palox_ids = fields.Many2many(related='production_id.palox_ids')
    farmers = fields.Char(related='production_id.farmers')
    season_id = fields.Many2one(related='production_id.season_id')
    oil_destination = fields.Selection(related='production_id.oil_destination')
    current_oil_product_id = fields.Many2one(
        related='production_id.oil_product_id', string='Current Oil Type')
    new_oil_product_id = fields.Many2one(
        'product.product', string='New Oil Type',
        domain="[('detailed_type', '=', 'olive_oil'), ('id', '!=', current_oil_product_id)]",
        required=True)
    sale_location_id = fields.Many2one(
        'stock.location', string='New Sale Tank', check_company=True,
        domain="[('olive_tank_type', '=', 'regular'), ('oil_product_id', '=', new_oil_product_id), ('olive_season_id', '=', season_id), ('company_id', '=', company_id)]",
        )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        assert self._context.get('active_model') == 'olive.oil.production'
        assert self._context.get('active_id')
        res['production_id'] = self._context['active_id']
        return res

    def validate(self):
        self.ensure_one()
        prod = self.production_id
        cur_product = self.current_oil_product_id
        cur_olive_culture_type = cur_product.olive_culture_type
        new_product = self.new_oil_product_id
        new_olive_culture_type = new_product.olive_culture_type
        if (
                cur_olive_culture_type in ('regular', 'conversion') and
                new_olive_culture_type == 'organic'):
            raise UserError(_(
                "You cannot swap oil type from a regular or conversion "
                "culture type to an organic culture type."))
        elif (
                cur_olive_culture_type in ('regular', 'organic') and
                new_olive_culture_type == 'conversion'):
            raise UserError(_(
                "You cannot swap oil type from a regular or organic "
                "culture type to a conversion culture type."))
        sloc = prod.warehouse_id.olive_get_shrinkage_tank(new_product)
        prod_vals = {
            'oil_product_id': new_product.id,
            'sale_location_id': self.sale_location_id.id or False,
            'shrinkage_location_id': sloc.id,
            }
        prod.write(prod_vals)
        prod.line_ids.write({'oil_product_id': new_product.id})
        prod.message_post(body=_(
            "Oil Type changed from <b>%s</b> to <b>%s</b> via the swap oil type wizard.")
            % (cur_product.name, new_product.name))
