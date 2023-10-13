# Copyright 2018-2023 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class OlivePaloxGenerateProduction(models.TransientModel):
    _name = 'olive.palox.generate.production'
    _description = 'Wizard to mass generation productions from palox'
    _check_company_auto = True

    company_id = fields.Many2one(
        'res.company', ondelete='cascade', required=True,
        default=lambda self: self.env.company)
    palox_ids = fields.Many2many('olive.palox', string='Paloxes', check_company=True)
    date = fields.Date(
        default=fields.Date.context_today, required=True)
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse', required=True, check_company=True,
        domain="[('olive_mill', '=', True), ('company_id', '=', company_id)]",
        default=lambda self: self.env.user._default_olive_mill_wh())

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        res['palox_ids'] = self.env.context.get('active_ids')
        return res

    def generate(self):
        self.ensure_one()
        if not self.palox_ids:
            raise UserError(_("No palox selected."))
        oopo = self.env['olive.oil.production']
        for palox in self.palox_ids:
            if not palox.oil_product_id:
                raise UserError(_(
                    "Missing oil product on palox '%s'.") % palox.display_name)
            vals = {
                'date': self.date,
                'palox_id': palox.id,
                'company_id': self.company_id.id,
                'warehouse_id': self.warehouse_id.id,
                }
            prod = oopo.create(vals)
            prod.draft2ratio()
        action = self.env['ir.actions.actions']._for_xml_id(
            'olive_mill.olive_oil_production_action')
        dayprods = oopo.search([('date', '=', self.date)])
        action['domain'] = [('id', 'in', dayprods.ids)]
        action['context'] = {'search_default_progress': True}
        return action
