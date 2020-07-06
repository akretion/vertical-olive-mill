# -*- coding: utf-8 -*-
# Copyright 2019 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError


class OliveAgrimerReport(models.Model):
    _name = 'olive.agrimer.report'
    _inherit = ['mail.thread']
    _description = 'Olive ARGIMER reports'
    _order = 'date_start desc'
    _rec_name = 'date_start'

    company_id = fields.Many2one(
        'res.company', string='Company',
        ondelete='cascade', required=True,
        states={'done': [('readonly', True)]},
        default=lambda self: self.env['res.company']._company_default_get())
    date_range_id = fields.Many2one(
        'date.range', string='Date Range',
        states={'done': [('readonly', True)]})
    date_start = fields.Date(
        string='Start Date', required=True, track_visibility='onchange',
        states={'done': [('readonly', True)]})
    date_end = fields.Date(
        string='End Date', track_visibility='onchange',
        required=True, states={'done': [('readonly', True)]})
    olive_arrival_qty = fields.Float(
        string='Olive Arrival (kg)', digits=dp.get_precision('Olive Weight'),
        states={'done': [('readonly', True)]})
    olive_pressed_qty = fields.Float(
        string='Olive Pressed (kg)', digits=dp.get_precision('Olive Weight'),
        states={'done': [('readonly', True)]})
    organic_virgin_oil_produced = fields.Float(
        string='Organic Virgin Olive Oil Produced (L)',
        digits=dp.get_precision('Olive Oil Volume'),
        states={'done': [('readonly', True)]})
    organic_extravirgin_oil_produced = fields.Float(
        string='Organic Extra Virgin Olive Oil Produced (L)',
        digits=dp.get_precision('Olive Oil Volume'),
        states={'done': [('readonly', True)]})
    regular_virgin_oil_produced = fields.Float(
        string='Regular Virgin Olive Oil Produced (L)',
        digits=dp.get_precision('Olive Oil Volume'),
        states={'done': [('readonly', True)]})
    regular_extravirgin_oil_produced = fields.Float(
        string='Regular Extra Virgin Olive Oil Produced (L)',
        digits=dp.get_precision('Olive Oil Volume'),
        states={'done': [('readonly', True)]})
    # Oil OUT
    # Shrinkage
    shrinkage_organic_virgin_oil = fields.Float(
        string='Shrinkage Organic Virgin Oil (L)',
        digits=dp.get_precision('Olive Oil Volume'),
        states={'done': [('readonly', True)]})
    shrinkage_organic_extravirgin_oil = fields.Float(
        string='Shrinkage Organic Extra Virgin Oil (L)',
        digits=dp.get_precision('Olive Oil Volume'),
        states={'done': [('readonly', True)]})
    shrinkage_regular_virgin_oil = fields.Float(
        string='Shrinkage Regular Virgin Oil (L)',
        digits=dp.get_precision('Olive Oil Volume'),
        states={'done': [('readonly', True)]})
    shrinkage_regular_extravirgin_oil = fields.Float(
        string='Shrinkage Regular Extra Virgin Oil (L)',
        digits=dp.get_precision('Olive Oil Volume'),
        states={'done': [('readonly', True)]})
    # WITHDRAWAL (product = oil /
    # selected source location wh.olive_withdrawal_loc_id)
    withdrawal_organic_virgin_oil = fields.Float(
        string='Withdrawal Organic Virgin Oil (L)',
        digits=dp.get_precision('Olive Oil Volume'),
        states={'done': [('readonly', True)]})
    withdrawal_organic_extravirgin_oil = fields.Float(
        string='Organic Extra Virgin Oil Withdrawal (L)',
        digits=dp.get_precision('Olive Oil Volume'),
        states={'done': [('readonly', True)]})
    withdrawal_regular_virgin_oil = fields.Float(
        string='Regular Virgin Oil Withdrawal (L)',
        digits=dp.get_precision('Olive Oil Volume'),
        states={'done': [('readonly', True)]})
    withdrawal_regular_extravirgin_oil = fields.Float(
        string='Regular Extra Virgin Oil Withdrawal (L)',
        digits=dp.get_precision('Olive Oil Volume'),
        states={'done': [('readonly', True)]})
    # CONSUMER sale (product = bottles /
    # no partner or partner with other pricelists)
    # we don't use fiscal positions, because the fp 'import/export dom-tom' can
    # we used both for B2C and B2B
    sale_consumer_organic_virgin_oil = fields.Float(
        string='Sale to Consumers of Organic Virgin Oil (L)',
        digits=dp.get_precision('Olive Oil Volume'),
        states={'done': [('readonly', True)]})
    sale_consumer_organic_extravirgin_oil = fields.Float(
        string='Sale to Consumers of Organic Extra Virgin Oil (L)',
        digits=dp.get_precision('Olive Oil Volume'),
        states={'done': [('readonly', True)]})
    sale_consumer_regular_virgin_oil = fields.Float(
        string='Sale to Consumers of Regular Virgin Oil (L)',
        digits=dp.get_precision('Olive Oil Volume'),
        states={'done': [('readonly', True)]})
    sale_consumer_regular_extravirgin_oil = fields.Float(
        string='Sale to Consumers of Regular Extra Virgin Oil (L)',
        digits=dp.get_precision('Olive Oil Volume'),
        states={'done': [('readonly', True)]})
    # DISTRIBUTOR sale (product = bottles / partner with selected pricelist)
    sale_distributor_organic_virgin_oil = fields.Float(
        string='Sale to Distributors of Organic Virgin Oil (L)',
        digits=dp.get_precision('Olive Oil Volume'),
        states={'done': [('readonly', True)]})
    sale_distributor_organic_extravirgin_oil = fields.Float(
        string='Sale to Distributors of Organic Extra Virgin Oil (L)',
        digits=dp.get_precision('Olive Oil Volume'),
        states={'done': [('readonly', True)]})
    sale_distributor_regular_virgin_oil = fields.Float(
        string='Sale to Distributors of Regular Virgin Oil (L)',
        digits=dp.get_precision('Olive Oil Volume'),
        states={'done': [('readonly', True)]})
    sale_distributor_regular_extravirgin_oil = fields.Float(
        string='Sale to Distributors of Regular Extra Virgin Oil (L)',
        digits=dp.get_precision('Olive Oil Volume'),
        states={'done': [('readonly', True)]})
    # LOOSE sale (product = oil / all other source locations)
    sale_loose_organic_virgin_oil = fields.Float(
        string='Loose Sale of Organic Virgin Oil (L)',
        digits=dp.get_precision('Olive Oil Volume'),
        states={'done': [('readonly', True)]})
    sale_loose_organic_extravirgin_oil = fields.Float(
        string='Loose Sale of Organic Extra Virgin Oil (L)',
        digits=dp.get_precision('Olive Oil Volume'),
        states={'done': [('readonly', True)]})
    sale_loose_regular_virgin_oil = fields.Float(
        string='Loose Sale of Regular Virgin Oil (L)',
        digits=dp.get_precision('Olive Oil Volume'),
        states={'done': [('readonly', True)]})
    sale_loose_regular_extravirgin_oil = fields.Float(
        string='Loose Sale of Regular Extra Virgin Oil (L)',
        digits=dp.get_precision('Olive Oil Volume'),
        states={'done': [('readonly', True)]})

    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ], default='draft', readonly=True, track_visibility='onchange')

    _sql_constraints = [(
        'date_company_uniq',
        'unique(date_start, date_end, company_id)',
        'An AgriMer report with the same start/end date already exists!')]

    @api.onchange('date_range_id')
    def onchange_date_range_id(self):
        if self.date_range_id:
            self.date_start = self.date_range_id.date_start
            self.date_end = self.date_range_id.date_end

    def draft2done(self):
        self.ensure_one()
        assert self.state == 'draft'
        self.state = 'done'

    def back2draft(self):
        self.ensure_one()
        assert self.state == 'done'
        self.state = 'draft'

    def _compute_olive_arrival_qty(self, vals):
        rg = self.env['olive.arrival.line'].read_group([
            ('arrival_date', '>=', self.date_start),
            ('arrival_date', '<=', self.date_end),
            ('arrival_state', '=', 'done'),
            ('company_id', '=', self.company_id.id),
            ], ['olive_qty'], [])
        vals['olive_arrival_qty'] = rg and rg[0]['olive_qty'] or 0.0

    def _compute_olive_pressed_qty(self, vals):
        rg = self.env['olive.arrival.line'].read_group([
            ('production_date', '>=', self.date_start),
            ('production_date', '<=', self.date_end),
            ('production_state', '=', 'done'),
            ('company_id', '=', self.company_id.id),
            ], ['olive_qty'], [])
        vals['olive_pressed_qty'] = rg and rg[0]['olive_qty'] or 0.0

    def _compute_oil_produced(self, vals, oiltype2oilproducts):
        for oil_type, oil_products in oiltype2oilproducts.items():
            net_fieldname = '%s_oil_produced' % oil_type
            shrinkage_fieldname = 'shrinkage_%s_oil' % oil_type
            rg = self.env['olive.arrival.line'].read_group([
                ('oil_product_id', 'in', oil_products.ids),
                ('production_date', '>=', self.date_start),
                ('production_date', '<=', self.date_end),
                ('production_state', '=', 'done'),
                ('company_id', '=', self.company_id.id),
                ], ['oil_qty_net', 'shrinkage_oil_qty'], [])
            vals[net_fieldname] = rg and rg[0]['oil_qty_net'] or 0.0
            vals[shrinkage_fieldname] =\
                rg and rg[0]['shrinkage_oil_qty'] or 0.0

    def _compute_oil_out(
            self, vals, oiltype2oilproducts, bottle2oiltypevol):
        smo = self.env['stock.move']
        move_common_domain = [
            ('state', '=', 'done'),
            ('date', '>=', self.date_start + ' 00:00:00'),
            ('date', '<=', self.date_end + ' 23:59:59'),
            ('company_id', '=', self.company_id.id),
            ]
        # Withdrawal
        olive_whs = self.env['stock.warehouse'].search([
            ('olive_mill', '=', True),
            ('olive_withdrawal_loc_id', '!=', False),
            ('company_id', '=', self.company_id.id)])
        withdrawal_locs = self.env['stock.location']
        for olive_wh in olive_whs:
            withdrawal_locs += olive_wh.olive_withdrawal_loc_id
        for oil_type, oil_products in oiltype2oilproducts.items():
            move_rg = smo.read_group(
                move_common_domain + [
                    ('product_id', 'in', oil_products.ids),
                    ('location_id', 'in', withdrawal_locs.ids),
                    ('location_dest_id.usage', '=', 'customer'),
                ], ['product_uom_qty'], [])
            return_move_rg = smo.read_group(
                move_common_domain + [
                    ('product_id', 'in', oil_products.ids),
                    ('location_id.usage', '=', 'customer'),
                    ('location_dest_id', 'in', withdrawal_locs.ids),
                ], ['product_uom_qty'], [])
            qty = move_rg and move_rg[0]['product_uom_qty'] or 0.0
            return_qty = return_move_rg and\
                return_move_rg[0]['product_uom_qty'] or 0.0
            withdrawal_fieldname = 'withdrawal_%s_oil' % oil_type
            vals[withdrawal_fieldname] = qty - return_qty
        # Loose
        for oil_type, oil_products in oiltype2oilproducts.items():
            move_rg = smo.read_group(
                move_common_domain + [
                    ('product_id', 'in', oil_products.ids),
                    ('location_id', 'not in', withdrawal_locs.ids),
                    ('location_dest_id.usage', '=', 'customer'),
                ], ['product_uom_qty'], [])
            return_move_rg = smo.read_group(
                move_common_domain + [
                    ('product_id', 'in', oil_products.ids),
                    ('location_id.usage', '=', 'customer'),
                    ('location_dest_id', 'not in', withdrawal_locs.ids),
                ], ['product_uom_qty'], [])
            loose_fieldname = 'sale_loose_%s_oil' % oil_type
            qty = move_rg and move_rg[0]['product_uom_qty'] or 0.0
            return_qty = return_move_rg and\
                return_move_rg[0]['product_uom_qty'] or 0.0
            vals[loose_fieldname] = qty - return_qty
        # Sale bottles
        rpo = self.env['res.partner']
        distri_pricelists = self.env['product.pricelist'].search([
            ('olive_oil_distributor', '=', True)])

        for bottle, props in bottle2oiltypevol.items():
            move_rg = smo.read_group(
                move_common_domain + [
                    ('product_id', '=', bottle.id),
                    ('location_id.usage', '=', 'internal'),
                    ('location_dest_id.usage', '=', 'customer'),
                ], ['product_uom_qty', 'partner_id'], ['partner_id'])
            return_move_rg = smo.read_group(
                move_common_domain + [
                    ('product_id', '=', bottle.id),
                    ('location_id.usage', '=', 'customer'),
                    ('location_dest_id.usage', '=', 'internal'),
                ], ['product_uom_qty', 'partner_id'], ['partner_id'])
            for return_r in return_move_rg:
                return_r['product_uom_qty'] *= -1
            for r in move_rg + return_move_rg:
                product_qty = r['product_uom_qty']
                if r['partner_id'] and distri_pricelists:
                    partner = rpo.browse(r['partner_id'][0])
                    if (
                            partner.property_product_pricelist and
                            partner.property_product_pricelist in
                            distri_pricelists):
                        self._oil_out_sale_final_compute(
                            'distributor', vals, props, product_qty)
                    else:
                        self._oil_out_sale_final_compute(
                            'consumer', vals, props, product_qty)
                else:
                    self._oil_out_sale_final_compute(
                        'consumer', vals, props, product_qty)

    def _oil_out_sale_final_compute(
            self, partner_type, vals, props, product_qty):
        for oil_type, vol in props.items():
            fieldname = 'sale_%s_%s_oil' % (partner_type, oil_type)
            vals[fieldname] += product_qty * vol

    def report_compute_values(self):
        oil_product_domain = {
            'organic_virgin': [
                ('olive_oil_type', '=', 'virgin'),
                ('olive_culture_type', 'in', ('organic', 'conversion'))],
            'organic_extravirgin': [
                ('olive_oil_type', '=', 'extravirgin'),
                ('olive_culture_type', 'in', ('organic', 'conversion'))],
            'regular_virgin': [
                ('olive_oil_type', '=', 'virgin'),
                ('olive_culture_type', '=', 'regular')],
            'regular_extravirgin': [
                ('olive_oil_type', '=', 'extravirgin'),
                ('olive_culture_type', '=', 'regular')],
            }
        oiltype2oilproducts = {}
        bottle2oiltypevol = {}
        ppo = self.env['product.product']
        for oil_type, domain in oil_product_domain.items():
            oiltype2oilproducts[oil_type] = ppo.search(
                domain + [('olive_type', '=', 'oil')])
        regular_bottles = ppo.search([('olive_type', '=', 'bottle_full')])
        for bottle in regular_bottles:
            bom, oil_product, bottle_volume =\
                bottle.oil_bottle_full_get_bom_and_oil_product()
            if not oil_product.olive_oil_type:
                raise UserError(_(
                    "Oil type not configured on oil product '%s'.")
                    % oil_product.display_name)
            if not oil_product.olive_culture_type:
                raise UserError(_(
                    "Culture type not configured on oil product '%s'.")
                    % oil_product.display_name)
            culture_type = oil_product.olive_culture_type
            if culture_type == 'conversion':
                culture_type = 'organic'
            oil_type = '%s_%s' % (culture_type, oil_product.olive_oil_type)
            bottle2oiltypevol[bottle] = {oil_type: bottle_volume}

        pack_bottles = ppo.search([('olive_type', '=', 'bottle_full_pack')])
        for pbottle in pack_bottles:
            bottle2oiltypevol[pbottle] = {}
            pack_dict = pbottle.oil_bottle_full_pack_get_bottles()
            for cbottle, qty in pack_dict.items():
                oil_type, bottle_volume = bottle2oiltypevol[cbottle].items()[0]
                if oil_type in bottle2oiltypevol[pbottle]:
                    bottle2oiltypevol[pbottle][oil_type] += bottle_volume * qty
                else:
                    bottle2oiltypevol[pbottle][oil_type] = bottle_volume * qty

        pack_bottles_kit = ppo.search(
            [('olive_type', '=', 'bottle_full_pack_phantom')])
        # Here, we just do a check to be sure that it's properly configured
        # But it has no impact on computation, because kits
        # appear as separate components in stock moves
        for pbottles_kit in pack_bottles_kit:
            boms = self.env['mrp.bom'].search([
                ('product_tmpl_id', '=', pbottles_kit.product_tmpl_id.id),
                ('type', '=', 'phantom'),
                ('product_uom_id', '=', pbottles_kit.uom_id.id),
            ])
            if not boms:
                raise UserError(_(
                    "No bill of material with type kit for product '%s'.")
                    % pbottles_kit.display_name)

        vals = {}
        self._reset_values(vals)
        self._compute_olive_arrival_qty(vals)
        self._compute_olive_pressed_qty(vals)
        self._compute_oil_produced(vals, oiltype2oilproducts)
        self._compute_oil_out(
            vals, oiltype2oilproducts, bottle2oiltypevol)
        return vals

    def _reset_values(self, vals):
        ffields = self.env['ir.model.fields'].search([
            ('model', '=', self._name),
            ('ttype', '=', 'float')])
        for ffield in ffields:
            vals[ffield.name] = 0.0

    def generate_report(self):
        vals = self.report_compute_values()
        self.write(vals)
        self.message_post(_("AgriMer report generated."))

    def olive_stock_levels(self, vals):
        vals['olive_stock_start']
