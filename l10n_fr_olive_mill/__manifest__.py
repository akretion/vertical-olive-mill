# -*- coding: utf-8 -*-
# Copyright 2019 Barroux Abbey (https://www.barroux.org/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'French localization for olive mill',
    'version': '12.0.1.0.0',
    'category': 'Manufacturing',
    'license': 'AGPL-3',
    'summary': 'AgriMer reports on olive mill',
    'author': 'Akretion,Barroux Abbey',
    'website': 'https://github.com/akretion/vertical-olive-mill',
    'depends': [
        'olive_mill',
        'date_range',
        ],
    'data': [
        'security/olive_security.xml',
        'security/ir.model.access.csv',
        'views/olive_agrimer_report.xml',
        'views/product.xml',
        'views/product_pricelist.xml',
    ],
    'installable': True,
    'application': True,
}
