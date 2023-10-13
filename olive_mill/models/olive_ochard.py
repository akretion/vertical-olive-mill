# Copyright 2018-2023 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, fields


class OliveOchard(models.Model):
    _name = 'olive.ochard'
    _description = 'Olive Ochard'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True)
    partner_id = fields.Many2one(
        'res.partner', string='Olive Farmer', ondelete='cascade', index=True,
        domain=[('parent_id', '=', False), ('olive_farmer', '=', True)])
    active = fields.Boolean(default=True)
    city = fields.Char('City')
    parcel_ids = fields.One2many(
        'olive.parcel', 'ochard_id', string='Parcels')
    tree_total = fields.Integer(
        compute='_compute_totals', string='Total Trees', readonly=True, store=True)
    area_total = fields.Float(
        compute='_compute_totals', string='Total Area', readonly=True, store=True,
        digits='Olive Parcel Area')

    _sql_constraints = [(
        'name_partner_id_unique',
        'unique(partner_id, name)',
        'This ochard already exists for this partner.')]

    @api.depends('parcel_ids.tree_qty', 'parcel_ids.area')
    def _compute_totals(self):
        for ochard in self:
            area = 0.0
            tree = 0
            for parcel in ochard.parcel_ids:
                tree += parcel.tree_qty
                area += parcel.area
            ochard.tree_total = tree
            ochard.area_total = area

    @api.depends('name', 'city')
    def name_get(self):
        res = []
        for ochard in self:
            name = ochard.name
            if ochard.city:
                name = u'%s (%s)' % (name, ochard.city)
            res.append((ochard.id, name))
        return res
