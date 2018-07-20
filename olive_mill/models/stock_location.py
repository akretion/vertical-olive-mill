# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
import odoo.addons.decimal_precision as dp


class StockLocation(models.Model):
    _inherit = 'stock.location'

    olive_type = fields.Selection([
        ('palox', 'Palox'),  # palox = pallet box
        ('tank', 'Tank'),
        ('ochard', 'Ochard'),
        ], string='Olive Mill Type')
    olive_borrower_partner_id = fields.Many2one(
        'res.partner', string='Borrower', ondelete='restrict', copy=False,
        domain=[('parent_id', '=', False)])
    olive_borrowed_date = fields.Date('Borrowed Date')
    olive_zip_id = fields.Many2one('res.better.zip', 'City/Zip Shortcut')
    olive_city = fields.Char('City')
    olive_parcel_ids = fields.One2many(
        'olive.parcel', 'location_id', string='Parcels')
    olive_tree_total = fields.Integer(
        compute='_compute_olive_parcel', string='Total Trees', readonly=True, store=True)
    olive_area_total = fields.Float(
        compute='_compute_olive_parcel', string='Total Area', readonly=True, store=True,
        digits=dp.get_precision('Area'))
    olive_cultivation_ids = fields.One2many(
        'olive.cultivation', 'location_id', string='Cultivation Methods')

    @api.constrains('olive_type', 'olive_borrower_partner_id')
    def olive_type_check(self):
        for loc in self:
            if loc.olive_borrower_partner_id and loc.olive_type != 'palox':
                raise ValidationError(_(
                    "The Borrower field should only be used for a palox stock location."))
            if loc.olive_type == 'ochard':
                if not self.partner_id:
                    raise UserError(_(
                        "Ochard '%s' must be linked to a partner.") % self.display_name)
                elif self.partner_id.parent_id:
                    raise UserError(_(
                        "Ochard '%s' must be linked to a parent partner, not to a contact.")
                        % self.display_name)

    @api.depends('olive_parcel_ids.tree_qty', 'olive_parcel_ids.area')
    def _compute_olive_parcel(self):
        for loc in self:
            area = 0.0
            tree = 0
            for parcel in loc.olive_parcel_ids:
                tree += parcel.tree_qty
                area += parcel.area
            loc.olive_tree_total = tree
            loc.olive_area_total = area

    @api.onchange('olive_zip_id')
    def olive_zip_id_onchange(self):
        if self.olive_zip_id:
            name = self.olive_zip_id.city
            if self.olive_zip_id.name:
                name = u'%s %s' % (self.olive_zip_id.name, name)
            self.olive_city = name

    @api.onchange('olive_type')
    def olive_type_change(self):
        if self.olive_type == 'ochard':
            res = {'domain': {'partner_id': [('parent_id', '=', False), ('olive_farmer', '=', True)]}}
            return res
