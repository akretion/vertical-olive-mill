# Copyright 2026 Akretion France (https://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo.tests.common import TransactionCase
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestOliveMill(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

    def test_create_olive_products(self):
        p1 = self.env['product.product'].create({
            'name': 'test olive product',
            'detailed_type': 'olive_oil',
            'olive_culture_type': 'regular',
            'default_code': 'TEST_OLIVE_PRODUCT1',
            'uom_id': self.env.ref('uom.product_uom_litre').id,
            'uom_po_id': self.env.ref('uom.product_uom_litre').id,
            })
        self.assertEqual(p1.type, 'consu')
#        self.assertTrue(p1.is_storable)
#        self.assertEqual(p1.tracking, 'lot')
