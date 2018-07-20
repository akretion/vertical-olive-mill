# -*- coding: utf-8 -*-
# Copyright 2018 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Olive Mill',
    'version': '10.0.1.0.0',
    'category': 'Manufacturing',  # Sales, Warehouse, Manufacturing, Purchases, Human Resources
    'license': 'AGPL-3',
    'summary': 'Manage an olive mill',
    'author': 'Akretion,Barroux Abbey',
    'website': 'https://github.com/akretion/vertical-olive-mill',
    'depends': [
        'mrp',
        'account',
        'product_expiry_simple',
        'base_location',
        #'stock_no_negative',  # ??
        #'date_range',  # for campaigns
        ],
    'data': [
        'security/olive_security.xml',
        'security/ir.model.access.csv',
        'data/decimal_precision.xml',
        'views/menu.xml',
        'wizard/mrp_product_produce_view.xml',
#        'views/stock_config_settings.xml',
        'views/stock_location.xml',
        'views/olive_parcel.xml',
        'views/olive_season.xml',
        'views/olive_lended_case.xml',
        'views/olive_cultivation.xml',
        'views/olive_treatment.xml',
        'views/partner.xml',
        'views/product.xml',
        'views/organic_certifying_entity.xml',
        'views/partner_organic_certification.xml',
        'views/stock_production_lot.xml',
        'views/mrp_production.xml',
    ],
    'demo': [
        'demo/product.xml',
        'demo/stock_location.xml',
        'demo/olive_season.xml',
        'demo/olive_treatment.xml',
        'demo/olive_parcel.xml',
        ],
    'installable': True,
    'application': True,
}
