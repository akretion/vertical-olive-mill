# Copyright 2019-2023 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models
from odoo.tools import float_is_zero


class OlivePartnerWarningPrint(models.TransientModel):
    _name = 'olive.partner.warning.print'
    _description = 'Wizard to print list of olive farmer warnings'
    _check_company_auto = True

    company_id = fields.Many2one(
        'res.company', ondelete='cascade', required=True,
        default=lambda self: self.env.company)
    season_id = fields.Many2one(
        'olive.season', string='Season', required=True, check_company=True,
        default=lambda self: self.env.company.current_season_id.id,
        domain="[('company_id', '=', company_id)]")

    def report_get_lines(self):
        self.ensure_one()
        res = []
        prec = self.env['decimal.precision'].precision_get('Olive Weight')
        partners = self.env['res.partner'].with_context(season_id=self.season_id.id).search(
            [('parent_id', '=', False), ('olive_farmer', '=', True)])
        for p in partners:
            olive_qty = p.olive_qty_current_season
            if (
                    not float_is_zero(olive_qty, precision_digits=prec) and
                    (p.olive_cultivation_form_ko or
                     p.olive_parcel_ko or
                     p.olive_organic_certif_ko or
                     p.olive_invoicing_ko or
                     p.olive_withdrawal_ko)):
                res.append({
                    'name': p.name_title,
                    'olive_qty': int(round(olive_qty, 0)),
                    'olive_qty_triturated': int(round(p.olive_qty_triturated_current_season, 0)),
                    'cultivation_form': p.olive_cultivation_form_ko and 'X' or '',
                    'parcel': p.olive_parcel_ko and 'X' or '',
                    'organic_certif': p.olive_organic_certif_ko and 'X' or '',
                    'invoicing': p.olive_invoicing_ko and 'X' or '',
                    'withdrawal': p.olive_withdrawal_ko and 'X' or '',
                    })
        return res
