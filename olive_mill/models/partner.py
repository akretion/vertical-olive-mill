# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
import odoo.addons.decimal_precision as dp


class ResPartner(models.Model):
    _inherit = 'res.partner'

    olive_farmer = fields.Boolean('Olive Farmer')
    olive_ochard_ids = fields.One2many(
        'olive.ochard', 'partner_id', string='Olive Ochards')
    olive_tree_total = fields.Integer(
        compute='_compute_olive_total', string='Total Trees', readonly=True)
    olive_area_total = fields.Float(
        compute='_compute_olive_total', string='Total Area', readonly=True,
        digits=dp.get_precision('Olive Parcel Area'))
    olive_lended_palox = fields.Integer(
        compute='_compute_olive_total', string='Lended Palox', readonly=True)
    olive_lended_regular_case = fields.Integer(
        compute='_compute_olive_total', string='Lended Regular Case', readonly=True)
    olive_lended_organic_case = fields.Integer(
        compute='_compute_olive_total', string='Lended Organic Case', readonly=True)
    olive_current_season_id = fields.Many2one(
        'olive.season', compute='_compute_olive_total', readonly=True,
        string='Current Olive Season')
    olive_qty_current_season = fields.Float(
        compute='_compute_olive_total', string='Olive Qty Brought',
        readonly=True, digits=dp.get_precision('Olive Weight'),
        help="Olives brought for the current season in kg")
    olive_qty_triturated_current_season = fields.Float(
        compute='_compute_olive_total', string='Olive Qty Triturated',
        readonly=True, digits=dp.get_precision('Olive Weight'),
        help="Olives triturated for the current season in kg")
    olive_qty_sale_current_season = fields.Float(
        compute='_compute_olive_total', string='Olive Qty Sold',
        readonly=True, digits=dp.get_precision('Olive Weight'),
        help="Equivalent in olive qty (in kg) of the oil sold during the current season")
    olive_qty_withdrawal_current_season = fields.Float(
        compute='_compute_olive_total', string='Olive Qty Withdrawal',
        readonly=True, digits=dp.get_precision('Olive Weight'),
        help="Equivalent in olive qty (in kg) of the withdrawal oil during the current season")
    olive_oil_qty_current_season = fields.Float(
        compute='_compute_olive_total', string='Net Oil Qty', readonly=True,
        digits=dp.get_precision('Olive Oil Volume'),
        help="Net olive oil producted for the current season in liters")
    olive_oil_ratio_current_season = fields.Float(
        compute='_compute_olive_total', string='Net Oil Ratio', readonly=True,
        digits=dp.get_precision('Olive Oil Ratio'),
        help="Net oil ratio for the current season in percentage")
    olive_oil_qty_withdrawal_current_season = fields.Float(
        compute='_compute_olive_total', string='Withdrawal Oil Qty', readonly=True,
        digits=dp.get_precision('Olive Oil Volume'),
        help="Withdrawal oil (already withdrawn and pending withdrawal) for the current season in liters")
    olive_oil_qty_to_withdraw = fields.Float(
        compute='_compute_olive_total', string='Oil Qty to Withdraw', readonly=True,
        digits=dp.get_precision('Olive Oil Volume'),
        help="Olive oil to withdraw in liters")
    olive_oil_qty_withdrawn_current_season = fields.Float(
        compute='_compute_olive_total', string='Withdrawn Oil Qty', readonly=True,
        digits=dp.get_precision('Olive Oil Volume'),
        help="Withdrawn oil for the current season in liters")
    olive_sale_oil_qty_current_season = fields.Float(
        compute='_compute_olive_total', string='Oil Qty Sold', readonly=True,
        digits=dp.get_precision('Olive Oil Volume'),
        help="Sold olive oil for the current season in liters")
    olive_cultivation_form_ko = fields.Boolean(
        compute='_compute_organic_and_warnings',
        string='Cultivation Form Missing', readonly=True)
    olive_parcel_ko = fields.Boolean(
        compute='_compute_organic_and_warnings',
        string='Parcel Information Incomplete', readonly=True)
    olive_organic_certif_ko = fields.Boolean(
        compute='_compute_organic_and_warnings',
        string='Organic Certification Missing', readonly=True)
    olive_invoicing_ko = fields.Boolean(
        compute='_compute_organic_and_warnings',
        string='Invoicing to do', readonly=True)
    olive_organic_certification_ids = fields.One2many(
        'partner.organic.certification', 'partner_id', 'Organic Certifications')
    olive_culture_type = fields.Selection([
        ('regular', 'Regular'),
        ('organic', 'Organic'),
        ('conversion', 'Conversion'),
        ], compute='_compute_organic_and_warnings',
        string='Olive Culture Type', readonly=True)
    olive_organic_certified_logo = fields.Binary(
        compute='_compute_organic_and_warnings',
        string='Organic Certified Logo', readonly=True)
    olive_sale_pricelist_id = fields.Many2one(
        'olive.sale.pricelist', string='Sale Pricelist for Olive Mill',
        company_dependent=True)

    @api.onchange('olive_farmer')
    def olive_farmer_change(self):
        if self.olive_farmer:
            self.customer = True
            self.supplier = True

    @api.one
    def _compute_olive_total(self):
        olive_lended_regular_case = 0
        olive_lended_organic_case = 0
        olive_lended_palox = 0
        olive_tree_total = 0
        olive_area_total = 0.0
        olive_qty_current_season = 0.0
        olive_qty_sale_current_season = 0.0
        olive_qty_withdrawal_current_season = 0.0
        olive_current_season_id = False
        olive_qty_triturated_current_season = 0.0
        olive_sale_oil_qty_current_season = 0.0
        olive_oil_qty_current_season = 0.0
        olive_oil_qty_withdrawal_current_season = 0.0
        olive_oil_ratio_current_season = 0.0
        olive_oil_qty_to_withdraw = 0.0
        olive_oil_qty_withdrawn_current_season = 0.0
        if self.olive_farmer:
            company = self.env.user.company_id
            cases_res = self.env['olive.lended.case'].read_group([
                ('company_id', '=', company.id),
                ('partner_id', '=', self.id)],
                ['regular_qty', 'organic_qty'], [])
            if cases_res:
                olive_lended_regular_case = cases_res[0]['regular_qty'] or 0
                olive_lended_organic_case = cases_res[0]['organic_qty'] or 0
            olive_lended_palox = self.env['olive.palox'].search([
                ('borrower_partner_id', '=', self.id),
                ('company_id', '=', company.id),
                ], count=True)

            parcel_res = self.env['olive.parcel'].read_group([
                ('partner_id', '=', self.id)],
                ['tree_qty', 'area'], [])
            if parcel_res:
                olive_tree_total = parcel_res[0]['tree_qty'] or 0.0
                olive_area_total = parcel_res[0]['area'] or 0.0

            season_id = self._context.get('season_id')
            if not season_id:
                season = self.env['olive.season'].get_current_season()
                if season:
                    season_id = season.id

            if season_id:
                olive_current_season_id = season_id
                arrival_res = self.env['olive.arrival.line'].read_group([
                    ('season_id', '=', season_id),
                    ('commercial_partner_id', '=', self.id),
                    ('state', '=', 'done')],
                    ['olive_qty'], [])
                if arrival_res:
                    olive_qty_current_season = arrival_res[0]['olive_qty'] or 0.0
                arrival_prod_res = self.env['olive.arrival.line'].read_group([
                    ('season_id', '=', season_id),
                    ('commercial_partner_id', '=', self.id),
                    ('state', '=', 'done'),
                    ('production_state', '=', 'done')],
                    ['olive_qty', 'sale_olive_qty', 'withdrawal_olive_qty', 'sale_oil_qty', 'oil_qty_net', 'withdrawal_oil_qty_with_compensation'],
                    [])
                if arrival_prod_res:
                    olive_qty_triturated_current_season = arrival_prod_res[0]['olive_qty'] or 0.0
                    olive_qty_sale_current_season = arrival_prod_res[0]['sale_olive_qty'] or 0.0
                    olive_qty_withdrawal_current_season = arrival_prod_res[0]['withdrawal_olive_qty'] or 0.0
                    olive_sale_oil_qty_current_season = arrival_prod_res[0]['sale_oil_qty'] or 0.0
                    olive_oil_qty_current_season = arrival_prod_res[0]['oil_qty_net'] or 0.0
                    olive_oil_qty_withdrawal_current_season = arrival_prod_res[0]['withdrawal_oil_qty_with_compensation'] or 0.0
                    if olive_qty_triturated_current_season:
                        olive_oil_ratio_current_season = 100 * olive_oil_qty_current_season / olive_qty_triturated_current_season
            olive_products = self.env['product.product'].search([
                ('olive_type', '=', 'oil')])
            withdrawal_locations = self.env['stock.location'].search([
                ('olive_tank_type', '=', False), ('usage', '=', 'internal')])
            withdrawal_res = self.env['stock.quant'].read_group([
                ('location_id', 'in', withdrawal_locations.ids),
                ('product_id', 'in', olive_products.ids),
                ('owner_id', '=', self.id)],
                ['qty'], [])
            if withdrawal_res:
                olive_oil_qty_to_withdraw = withdrawal_res[0]['qty'] or 0.0
            olive_oil_qty_withdrawn_current_season = olive_oil_qty_withdrawal_current_season - olive_oil_qty_to_withdraw
        self.olive_lended_regular_case = olive_lended_regular_case
        self.olive_lended_organic_case = olive_lended_organic_case
        self.olive_lended_palox = olive_lended_palox
        self.olive_tree_total = olive_tree_total
        self.olive_area_total = olive_area_total
        self.olive_qty_current_season = olive_qty_current_season
        self.olive_qty_sale_current_season = olive_qty_sale_current_season
        self.olive_qty_withdrawal_current_season = olive_qty_withdrawal_current_season
        self.olive_current_season_id = olive_current_season_id
        self.olive_qty_triturated_current_season = olive_qty_triturated_current_season
        self.olive_sale_oil_qty_current_season = olive_sale_oil_qty_current_season
        self.olive_oil_qty_current_season = olive_oil_qty_current_season
        self.olive_oil_qty_withdrawal_current_season = olive_oil_qty_withdrawal_current_season
        self.olive_oil_ratio_current_season = olive_oil_ratio_current_season
        self.olive_oil_qty_to_withdraw = olive_oil_qty_to_withdraw
        self.olive_oil_qty_withdrawn_current_season = olive_oil_qty_withdrawn_current_season

    def _compute_organic_and_warnings(self):
        poco = self.env['partner.organic.certification']
        oco = self.env['olive.cultivation']
        ooo = self.env['olive.ochard']
        opo = self.env['olive.parcel']
        oalo = self.env['olive.arrival.line']
        parcel_required_fields = [
            'ochard_id',
            'land_registry_ref',
            'area',
            'tree_qty',
            'variant_label',
            # 'density', no warning if empty
            'planted_year',
            # 'irrigation', no warning if empty
            # 'cultivation_method', no warning if empty
            ]
        for partner in self:
            culture_type = 'regular'
            filename = False
            logo = False
            cultivation_form_ko = True
            parcel_ko = True
            certif_ko = False
            invoicing_ko = False
            if partner.olive_farmer and not partner.parent_id:
                # parcel_ok if all ochards have at least one parcel
                # and alls parcels have complete info
                ochard_ids = ooo.search([('partner_id', '=', partner.id)]).ids
                if ochard_ids:
                    parcels_complete = True
                    parcels = opo.search_read(
                        [('partner_id', '=', partner.id)],
                        parcel_required_fields)
                    for parcel in parcels:
                        if parcel.get('ochard_id'):
                            ochard_id = parcel['ochard_id'][0]
                            if ochard_id in ochard_ids:
                                ochard_ids.remove(ochard_id)
                        for pfield in parcel_required_fields:
                            if not parcel.get(pfield):
                                parcels_complete = False
                                break
                        if not parcels_complete:
                            break
                    if not ochard_ids and parcels_complete:
                        parcel_ko = False

                season_id = self._context.get('season_id')
                if not season_id:
                    season = self.env['olive.season'].get_current_season()
                    if season:
                        season_id = season.id

                if season_id:
                    cert = poco.search([
                        ('partner_id', '=', partner.id),
                        ('season_id', '=', season_id),
                        ], limit=1)
                    if cert:
                        if cert.conversion:
                            culture_type = 'conversion'
                            filename = 'organic_logo_conversion_done.png'
                            if cert.state == 'draft':
                                filename = 'organic_logo_conversion_draft.png'
                        else:
                            culture_type = 'organic'
                            filename = 'organic_logo_done.png'
                            if cert.state == 'draft':
                                filename = 'organic_logo_draft.png'
                    if cert.state == 'draft':
                        certif_ko = True

                    cultivations = oco.search([
                        ('season_id', '=', season_id),
                        ('partner_id', '=', partner.id)], limit=1)
                    if cultivations:
                        cultivation_form_ko = False
                    lines_to_out_invoice = oalo.search([
                        ('commercial_partner_id', '=', partner.id),
                        ('season_id', '=', season_id),
                        ('production_state', '=', 'done'),
                        ('out_invoice_id', '=', False),
                        ], count=True)
                    if lines_to_out_invoice:
                        invoicing_ko = True
                    else:
                        lines_to_in_invoice = oalo.search([
                            ('commercial_partner_id', '=', partner.id),
                            ('production_state', '=', 'done'),
                            ('in_invoice_line_id', '=', False),
                            ('oil_destination', 'in', ('sale', 'mix')),
                            ('sale_oil_qty', '>', 0),
                            ('season_id', '=', season_id),
                            ], count=True)
                        if lines_to_in_invoice:
                            invoicing_ko = True
            if filename:
                fname_path = 'olive_mill/static/image/%s' % filename
                f = tools.file_open(fname_path, 'rb')
                f_binary = f.read()
                if f_binary:
                    logo = f_binary.encode('base64')
            partner.olive_culture_type = culture_type
            partner.olive_organic_certified_logo = logo
            partner.olive_cultivation_form_ko = cultivation_form_ko
            partner.olive_parcel_ko = parcel_ko
            partner.olive_organic_certif_ko = certif_ko
            partner.olive_invoicing_ko = invoicing_ko

    def olive_check_in_invoice_fiscal_position(self):
        self.ensure_one()
        assert not self.parent_id
        if not self.vat and not self.property_account_position_id:
            raise UserError(_(
                "You are about to generate a supplier invoice for "
                "farmer '%s': you must enter his VAT number in Odoo "
                "or set a fiscal position corresponding to his "
                "fiscal situation (otherwise, we would "
                "purchase olive oil with VAT to a farmer "
                "that is not subject to VAT, which would be a big "
                "problem!).") % self.display_name)

    def update_organic_certif(self):
        self.ensure_one()
        cert = self.env['partner.organic.certification'].search([
            ('partner_id', '=', self.id),
            ('season_id', '=', self.env.user.company_id.current_season_id.id),
            ('state', '=', 'draft'),
            ], limit=1)
        action = self.env.ref('olive_mill.partner_organic_certification_action').read()[0]
        action['context'] = {
            'partner_organic_certification_main_view': True,
            'search_default_partner_id': self.id,
            'default_partner_id': self.id,
            }
        if cert:
            action.update({
                'view_mode': 'form,tree',
                'res_id': cert.id,
                'views': False,
                })
        return action

    def create_single_olive_ochard(self):
        self.ensure_one()
        assert not self.parent_id
        assert not self.olive_ochard_ids
        self.env['olive.ochard'].create({
            'partner_id': self.id,
            'name': _('OCHARD TO RENAME'),
            })
