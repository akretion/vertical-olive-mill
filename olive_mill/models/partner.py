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
        digits=dp.get_precision('Area'))
    olive_lended_palox = fields.Integer(
        compute='_compute_olive_total', string='Lended Palox', readonly=True)
    olive_lended_regular_case = fields.Integer(
        compute='_compute_olive_total', string='Lended Regular Case', readonly=True)
    olive_lended_organic_case = fields.Integer(
        compute='_compute_olive_total', string='Lended Organic Case', readonly=True)
    olive_organic_certification_ids = fields.One2many(
        'partner.organic.certification', 'partner_id', 'Organic Certifications')
    olive_organic_certified = fields.Selection([
        ('organic', 'Organic'),
        ('organic-draft', 'Organic (to confirm)'),
        ('convert', 'Convert'),
        ('convert-draft', 'Convert (to confirm)'),
        ], compute='_compute_olive_organic_certified',
        string='Organic Certified', readonly=True)
    olive_organic_certified_logo = fields.Binary(
        compute='_compute_olive_organic_certified',
        string='Organic Certified Logo', readonly=True)

    @api.onchange('olive_farmer')
    def olive_farmer_change(self):
        if self.olive_farmer:
            self.customer = True
            self.supplier = True

    def _compute_olive_total(self):
        cases_rg = []
        parels_rg = []
        try:
            cases_rg = self.env['olive.lended.case'].read_group([
                ('company_id', '=', self.env.user.company_id.id),
                ('partner_id', 'in', self.ids)],
                ['partner_id', 'regular_qty', 'organic_qty'], ['partner_id'])
        except Exception:
            pass
        try:
            parcels_rg = self.env['olive.parcel'].read_group([
                ('company_id', '=', self.env.user.company_id.id),
                ('partner_id', 'in', self.ids)],
                ['partner_id', 'tree_qty', 'area'], ['partner_id'])
        except Exception:
            pass

        for partner in self:
            tree = 0
            area = 0.0
            palox = 0
            regular_case = 0
            organic_case = 0

            if partner.olive_farmer and not partner.parent_id:
                for parcel_rg in parcels_rg:
                    if parcel_rg.get('partner_id') and parcel_rg['partner_id'][0] == partner.id:
                        tree = parcel_rg.get('tree_qty')
                        area = parcel_rg.get('area')
                        break
                try:
                    palox = self.env['stock.location'].search([
                        ('olive_type', '=', 'palox'),
                        ('olive_borrower_partner_id', '=', partner.id),
                        ], count=True)
                except Exception:
                    pass
                for case_rg in cases_rg:
                    if case_rg.get('partner_id') and case_rg['partner_id'][0] == partner.id:
                        regular_case = case_rg.get('regular_qty')
                        organic_case = case_rg.get('organic_qty')
                        break

            partner.olive_tree_total = tree
            partner.olive_area_total = area
            partner.olive_lended_palox = palox
            partner.olive_lended_regular_case = regular_case
            partner.olive_lended_organic_case = organic_case

    def _compute_olive_organic_certified(self):
        season = self.env['olive.season'].get_current_season()
        for partner in self:
            certified = False
            filename = False
            logo = False
            if season and partner.olive_farmer and not partner.parent_id:
                cert = self.env['partner.organic.certification'].search([
                    ('partner_id', '=', partner.id),
                    ('season_id', '=', season.id),
                    ], limit=1)
                if cert:
                    if cert.state == 'done':
                        if cert.convert:
                            certified = 'convert'
                            filename = 'organic_logo_convert_done.png'
                        else:
                            certified = 'organic'
                            filename = 'organic_logo_done.png'
                    elif cert.state == 'draft':
                        if cert.convert:
                            certified = 'convert-draft'
                            filename = 'organic_logo_convert_draft.png'
                        else:
                            certified = 'organic-draft'
                            filename = 'organic_logo_draft.png'
            if filename:
                fname_path = 'olive_mill/static/image/%s' % filename
                f = tools.file_open(fname_path, 'rb')
                f_binary = f.read()
                if f_binary:
                    logo = f_binary.encode('base64')
            partner.olive_organic_certified = certified
            partner.olive_organic_certified_logo = logo
