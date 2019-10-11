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
    olive_qty_current_season = fields.Integer(
        compute='_compute_olive_total', string='Olive Qty', readonly=True,
        help="Olive quantity for the current season in kg")
    olive_sale_oil_qty_current_season = fields.Float(
        compute='_compute_olive_total', string='Oil Qty Sold (L)', readonly=True,
        digits=dp.get_precision('Olive Oil Volume'),
        help="Olive oil sale quantity for the current season in liters")
    olive_cultivation_form_ko = fields.Boolean(
        compute='_compute_organic_and_warnings',
        string='Cultivation Form Missing', readonly=True)
    olive_parcel_ko = fields.Boolean(
        compute='_compute_organic_and_warnings',
        string='Parcel Information Incomplete', readonly=True)
    olive_organic_certif_ko = fields.Boolean(
        compute='_compute_organic_and_warnings',
        string='Organic Certification Missing', readonly=True)
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

    def _compute_olive_total(self):
        company = self.env.user.company_id
        cases_res = self.env['olive.lended.case'].read_group([
            ('company_id', '=', company.id),
            ('partner_id', 'in', self.ids)],
            ['partner_id', 'regular_qty', 'organic_qty'], ['partner_id'])
        for cases_re in cases_res:
            partner = self.browse(cases_re['partner_id'][0])
            partner.olive_lended_regular_case = cases_re['regular_qty']
            partner.olive_lended_organic_case = cases_re['organic_qty']
        parcel_res = self.env['olive.parcel'].read_group([
            ('partner_id', 'in', self.ids)],
            ['partner_id', 'tree_qty', 'area'], ['partner_id'])
        for parcel_re in parcel_res:
            partner = self.browse(parcel_re['partner_id'][0])
            partner.olive_tree_total = parcel_re['tree_qty']
            partner.olive_area_total = parcel_re['area']

        palox_res = self.env['olive.palox'].read_group([
            ('borrower_partner_id', 'in', self.ids),
            ('company_id', '=', company.id),
            ], ['borrower_partner_id'], ['borrower_partner_id'])
        for palox_re in palox_res:
            partner = self.browse(palox_re['borrower_partner_id'][0])
            partner.olive_lended_palox = palox_re['borrower_partner_id_count']
        season = self.env['olive.season'].get_current_season()
        if season:
            arrival_res = self.env['olive.arrival.line'].read_group([
                ('season_id', '=', season.id),
                ('commercial_partner_id', 'in', self.ids),
                ('state', '=', 'done')],
                ['commercial_partner_id', 'olive_qty', 'sale_oil_qty'],
                ['commercial_partner_id'])
            for arrival_re in arrival_res:
                partner = self.browse(arrival_re['commercial_partner_id'][0])
                partner.olive_qty_current_season = int(arrival_re['olive_qty'])
                partner.olive_sale_oil_qty_current_season = arrival_re['sale_oil_qty']
                partner.olive_current_season_id = season.id

    def _compute_organic_and_warnings(self):
        season = self.env['olive.season'].get_current_season()
        poco = self.env['partner.organic.certification']
        oco = self.env['olive.cultivation']
        ooo = self.env['olive.ochard']
        opo = self.env['olive.parcel']
        parcel_required_fields = [
            'ochard_id',
            'land_registry_ref',
            'area',
            'tree_qty',
            'variant_label',
            'density',
            'planted_year',
            'irrigation',
            'cultivation_method',
            ]
        for partner in self:
            culture_type = 'regular'
            filename = False
            logo = False
            cultivation_form_ko = True
            parcel_ko = True
            certif_ko = False
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

                if season:
                    cert = poco.search([
                        ('partner_id', '=', partner.id),
                        ('season_id', '=', season.id),
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
                        ('season_id', '=', season.id),
                        ('partner_id', '=', partner.id)], limit=1)
                    if cultivations:
                        cultivation_form_ko = False
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

