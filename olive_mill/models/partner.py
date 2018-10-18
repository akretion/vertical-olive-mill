# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
import odoo.addons.decimal_precision as dp


class ResPartner(models.Model):
    _inherit = 'res.partner'

    olive_farmer = fields.Boolean('Olive Farmer')
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
    olive_organic_certification_ids = fields.One2many(
        'partner.organic.certification', 'partner_id', 'Organic Certifications')
    olive_culture_type = fields.Selection([
        ('regular', 'Regular'),
        ('organic', 'Organic'),
        ('conversion', 'Conversion'),
        ], compute='_compute_olive_organic_certified',
        string='Olive Culture Type', readonly=True)
    olive_organic_certified_logo = fields.Binary(
        compute='_compute_olive_organic_certified',
        string='Organic Certified Logo', readonly=True)
    olive_sale_pricelist_id = fields.Many2one(
        'olive.sale.pricelist', string='Sale Pricelist', ondelete='restrict')

    @api.onchange('olive_farmer')
    def olive_farmer_change(self):
        if self.olive_farmer:
            self.customer = True
            self.supplier = True

    def _compute_olive_total(self):
        cases_rg = []
        parcels_rg = []
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

    def _compute_olive_organic_certified(self):
        season = self.env['olive.season'].get_current_season()
        for partner in self:
            culture_type = 'regular'
            filename = False
            logo = False
            if season and partner.olive_farmer and not partner.parent_id:
                cert = self.env['partner.organic.certification'].search([
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
            if filename:
                fname_path = 'olive_mill/static/image/%s' % filename
                f = tools.file_open(fname_path, 'rb')
                f_binary = f.read()
                if f_binary:
                    logo = f_binary.encode('base64')
            partner.olive_culture_type = culture_type
            partner.olive_organic_certified_logo = logo
