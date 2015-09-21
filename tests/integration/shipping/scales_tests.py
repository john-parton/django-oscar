from decimal import Decimal as D

from django.test import TestCase

from oscar.apps.shipping.scales import Scale
from oscar.apps.basket.models import Basket
from oscar.test import factories


class TestScales(TestCase):

    def setUp(self):
        self.weight = factories.ProductAttributeFactory()
        self.product_class = self.weight.product_class
        self.scale = Scale(attribute_code='weight')
        self.scale_with_default = Scale(attribute_code='weight', default_weight=0.5)

    def _create_product_with_weight(self, weight=None):
        __, product, __ = factories.create_product_heirarchy(product_class=self.product_class.name)
        if weight is not None:
            product.attr.weight = weight
            product.save()
        return product

    def test_weighs_uses_specified_attribute(self):
        product = self._create_product_with_weight(weight=1)
        self.assertEqual(1, self.scale.weigh_product(product))

    def test_uses_default_weight_when_attribute_is_missing(self):
        product = self._create_product_with_weight(weight=None)
        self.assertEqual(0.5, self.scale_with_default.weigh_product(product))

    def test_raises_exception_when_attribute_is_missing(self):
        product = self._create_product_with_weight(weight=None)
        with self.assertRaises(ValueError):
            self.scale.weigh_product(product)

    def test_returns_zero_for_empty_basket(self):
        basket = Basket()
        self.assertEqual(0, self.scale.weigh_basket(basket))

    def test_returns_correct_weight_for_nonempty_basket(self):
        basket = factories.create_basket(empty=True)

        for weight in ('1', '2'):
            product = self._create_product_with_weight(weight=weight)
            basket.add(product)

        self.assertEqual(1 + 2, self.scale.weigh_basket(basket))

    def test_returns_correct_weight_for_nonempty_basket_with_line_quantities(self):
        basket = factories.create_basket(empty=True)
        for weight, quantity in [('1', 3), ('2', 4)]:
            product = self._create_product_with_weight(weight=weight)
            basket.add(product, quantity=quantity)

        self.assertEqual(1*3 + 2*4, self.scale.weigh_basket(basket))
