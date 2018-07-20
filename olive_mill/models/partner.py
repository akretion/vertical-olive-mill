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
    olive_lended_case = fields.Integer(
        compute='_compute_olive_total', string='Lended Case', readonly=True)
    olive_organic_certification_ids = fields.One2many(
        'partner.organic.certification', 'partner_id', 'Organic Certifications')
    olive_organic_certified = fields.Boolean(
        compute='_compute_olive_organic_certified', string='Is Organic Certified', readonly=True)

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
                ['partner_id', 'qty'], ['partner_id'])
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
            case = 0

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
                        case = case_rg.get('qty')
                        break

            partner.olive_tree_total = tree
            partner.olive_area_total = area
            partner.olive_lended_palox = palox
            partner.olive_lended_case = case

    def _compute_olive_organic_certified(self):
        season = self.env['olive.season'].get_current_season()
        for partner in self:
            cert = False
            if season and partner.olive_farmer and not partner.parent_id:
                certs = self.env['partner.organic.certification'].search([
                    ('partner_id', '=', partner.id),
                    ('season_id', '=', season.id),
                    ('state', '=', 'done'),
                    ])
                if certs:
                    cert = True
            partner.olive_organic_certified = cert
