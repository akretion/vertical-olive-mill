# Copyright 2018-2023 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.tools import float_round
from odoo.exceptions import UserError


class OliveOilProductionRatio2force(models.TransientModel):
    _name = 'olive.oil.production.ratio2force'
    _description = 'Olive Oil Production Ratio2force'
    _check_company_auto = True

    production_id = fields.Many2one(
        'olive.oil.production', string='Olive Oil Production', required=True)
    company_id = fields.Many2one(related='production_id.company_id')
    result_uom = fields.Selection(
        related='production_id.company_id.olive_oil_production_result_uom')
    result_method = fields.Selection([
        ('per_palox', 'Per Palox'),
        ('global', 'Global'),
        ])
    farmers = fields.Char(related='production_id.farmers')
    palox_ids = fields.Many2many(related='production_id.palox_ids')
    season_id = fields.Many2one(related='production_id.season_id')
    oil_product_id = fields.Many2one(related='production_id.oil_product_id')
    oil_destination = fields.Selection(related='production_id.oil_destination')
    olive_qty = fields.Float(related='production_id.olive_qty')
    oil_qty_kg = fields.Float(
        compute="_compute_oil_qty_kg", store=True, readonly=False,
        string='Oil Qty (kg)', digits='Olive Weight')
    oil_qty = fields.Float(
        compute='_compute_oil_qty', store=True, readonly=False,
        string='Oil Qty (L)', digits='Olive Oil Volume')
    ratio = fields.Float(
        compute="_compute_ratio", store=True,
        string='Gross Ratio (% L)', digits='Olive Oil Ratio')
    sale_location_id = fields.Many2one(
        'stock.location', string='Sale Tank', check_company=True,
        domain="[('olive_tank_type', '=', 'regular'), ('oil_product_id', '=', oil_product_id), ('olive_season_id', '=', season_id), ('company_id', '=', company_id)]")
    decanter_duration = fields.Integer(string='Decanter Duration')
    decanter_speed = fields.Integer(
        string='Decanter Speed', compute='_compute_decanter_speed')
    palox_result_ids = fields.One2many(
        "olive.oil.production.ratio2force.line", "wizard_id", string="Per Palox Results")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        assert self._context.get('active_model') == 'olive.oil.production'
        assert self._context.get('active_id')
        res['production_id'] = self._context['active_id']
        prod = self.env['olive.oil.production'].browse(res['production_id'])
        if prod.sale_location_id:
            res['sale_location_id'] = prod.sale_location_id.id
        if len(prod.palox_ids) > 1 and prod.company_id.olive_oil_production_multipalox_result == 'per_palox':
            res['result_method'] = 'per_palox'
            res['palox_result_ids'] = [(0, 0, {"arrival_line_id": line.id}) for line in prod.line_ids]
        else:
            res['result_method'] = 'global'
        return res

    @api.depends('oil_qty_kg', 'palox_result_ids.oil_qty', 'result_method')
    def _compute_oil_qty(self):
        pr_oil = self.env['decimal.precision'].precision_get(
            'Olive Oil Volume')
        pr_olive = self.env['decimal.precision'].precision_get(
            'Olive Weight')
        for wiz in self:
            density = wiz.production_id.company_id.olive_oil_density
            oil_qty = 0.0
            if wiz.result_method == "per_palox":
                oil_qty = float_round(sum([l.oil_qty for l in wiz.palox_result_ids]), precision_digits=pr_oil)
                # also write oil_qty_kg
                wiz.oil_qty_kg = float_round(oil_qty * density, precision_digits=pr_olive)
            elif density:
                oil_qty = wiz.oil_qty_kg / density
            wiz.oil_qty = oil_qty

    @api.depends('oil_qty', 'palox_result_ids.oil_qty_kg', 'result_method')
    def _compute_oil_qty_kg(self):
        pr_oil = self.env['decimal.precision'].precision_get(
            'Olive Oil Volume')
        pr_olive = self.env['decimal.precision'].precision_get(
            'Olive Weight')
        for wiz in self:
            density = wiz.production_id.company_id.olive_oil_density
            oil_qty_kg = 0.0
            if wiz.result_method == "per_palox":
                oil_qty_kg = float_round(sum([l.oil_qty_kg for l in wiz.palox_result_ids]), precision_digits=pr_olive)
                # also write oil_qty
                if density:
                    wiz.oil_qty = float_round(oil_qty_kg / density, precision_digits=pr_oil)
            else:
                oil_qty_kg = wiz.oil_qty * density
                oil_qty_kg = float_round(oil_qty_kg, precision_digits=pr_olive)
            wiz.oil_qty_kg = oil_qty_kg

    @api.depends('oil_qty')
    def _compute_ratio(self):
        pr_ratio = self.env['decimal.precision'].precision_get('Olive Oil Ratio')
        for wiz in self:
            ratio = 0.0
            if wiz.olive_qty:
                ratio = float_round(100 * wiz.oil_qty / wiz.olive_qty, precision_digits=pr_ratio)
            wiz.ratio = ratio

    @api.depends('decanter_duration')
    def _compute_decanter_speed(self):
        for wiz in self:
            decanter_speed = 0
            if wiz.decanter_duration:
                decanter_speed = wiz.olive_qty * 60 / wiz.decanter_duration
            wiz.decanter_speed = decanter_speed

    def validate(self):
        self.ensure_one()
        prod = self.production_id
        min_ratio, max_ratio = prod.company_id.olive_min_max_ratio()
        if self.ratio > max_ratio or self.ratio < min_ratio:
            raise UserError(_(
                "The ratio (%s %%) of production %s is not realistic.")
                % (self.ratio, prod.name))
        vals = {
            'oil_qty_kg': self.oil_qty_kg,
            'oil_qty': self.oil_qty,
            'ratio': self.ratio,
            'decanter_speed': self.decanter_speed,
            'sale_location_id': self.sale_location_id.id or False,
            }
        prod.write(vals)
        prod.ratio2force()


class OliveOilProductionRatio2forceLine(models.TransientModel):
    _name = 'olive.oil.production.ratio2force.line'
    _description = 'Olive Oil Production Ratio2force Arrival Line'
    _check_company_auto = True

    wizard_id = fields.Many2one(
        'olive.oil.production.ratio2force', string='Wizard', ondelete='cascade')
    arrival_line_id = fields.Many2one("olive.arrival.line", readonly=True)
    palox_id = fields.Many2one(related="arrival_line_id.palox_id")
    olive_qty = fields.Float(related="arrival_line_id.olive_qty")
    oil_qty_kg = fields.Float(
        compute="_compute_oil_qty_kg", store=True, readonly=False,
        string='Oil Qty (kg)', digits='Olive Weight')
    oil_qty = fields.Float(
        compute='_compute_oil_qty', store=True, readonly=False,
        string='Oil Qty (L)', digits='Olive Oil Volume')
    ratio = fields.Float(
        compute="_compute_ratio", store=True, string='Gross Ratio (% L)',
        digits='Olive Oil Ratio')
    result_uom = fields.Selection(
        related='wizard_id.production_id.company_id.olive_oil_production_result_uom')

    @api.depends('oil_qty_kg')
    def _compute_oil_qty(self):
        pr_oil = self.env['decimal.precision'].precision_get('Olive Oil Volume')
        for wiz in self:
            density = wiz.wizard_id.production_id.company_id.olive_oil_density
            oil_qty = 0.0
            if density:
                oil_qty = float_round(wiz.oil_qty_kg / density, precision_digits=pr_oil)
            wiz.oil_qty = oil_qty

    @api.depends('oil_qty')
    def _compute_oil_qty_kg(self):
        pr_olive = self.env['decimal.precision'].precision_get('Olive Weight')
        for wiz in self:
            density = wiz.wizard_id.production_id.company_id.olive_oil_density
            oil_qty_kg = 0.0
            if density:
                oil_qty_kg = float_round(wiz.oil_qty * density, precision_digits=pr_olive)
            wiz.oil_qty_kg = oil_qty_kg

    @api.depends('oil_qty')
    def _compute_ratio(self):
        pr_ratio = self.env['decimal.precision'].precision_get('Olive Oil Ratio')
        for wiz in self:
            ratio = 0.0
            if wiz.olive_qty:
                ratio = float_round(100 * wiz.oil_qty / wiz.olive_qty, precision_digits=pr_ratio)
            wiz.ratio = ratio
