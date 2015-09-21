from django.test import TestCase

from oscar.apps.partner import strategy
from oscar.test import factories


class TestUseFirstStockRecordMixin(TestCase):

    def setUp(self):
        __, self.product, self.stockrecord = factories.create_product_heirarchy()
        self.mixin = strategy.UseFirstStockRecord()

    def test_selects_first_stockrecord_for_product(self):
        selected = self.mixin.select_stockrecord(self.product)
        self.assertEqual(selected.id, self.stockrecord.id)

    def test_returns_none_when_no_stock_records(self):
        self.stockrecord.delete()
        self.assertIsNone(self.mixin.select_stockrecord(self.product))
