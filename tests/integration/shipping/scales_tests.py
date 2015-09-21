from decimal import Decimal as D

from django.test import TestCase

from oscar.apps.shipping.scales import Scale
from oscar.apps.basket.models import Basket
from oscar.test import factories


class TestScales(TestCase):

    def test_weighs_uses_specified_attribute(self):
        scale = Scale(attribute_code='weight')
        __, product, __ = factories.create_product_heirarchy()
        product.attr.weight = 1
        product.save()
        self.assertEqual(1, scale.weigh_product(p))

    def test_uses_default_weight_when_attribute_is_missing(self):
        scale = Scale(attribute_code='weight', default_weight=0.5)
        __, product, __ = factories.create_product_heirarchy()
        self.assertEqual(0.5, scale.weigh_product(product))

    def test_raises_exception_when_attribute_is_missing(self):
        scale = Scale(attribute_code='weight')
        __, product, __ = factories.create_product_heirarchy()
        with self.assertRaises(ValueError):
            scale.weigh_product(product)

    def test_returns_zero_for_empty_basket(self):
        basket = Basket()

        scale = Scale(attribute_code='weight')
        self.assertEqual(0, scale.weigh_basket(basket))

    def test_returns_correct_weight_for_nonempty_basket(self):
        basket = factories.create_basket(empty=True)

        for weight in ('1', '2'):
            __, product, __ = factories.create_product_heirarchy()
            product.attr.weight = weight
            product.save()
            basket.add(product)

        scale = Scale(attribute_code='weight')
        self.assertEqual(1 + 2, scale.weigh_basket(basket))

    def test_returns_correct_weight_for_nonempty_basket_with_line_quantities(self):
        basket = factories.create_basket(empty=True)
        products = [
            (factories.create_product(attributes={'weight': '1'},
                                      price=D('5.00')), 3),
            (factories.create_product(attributes={'weight': '2'},
                                      price=D('5.00')), 4)]
        for product, quantity in products:
            basket.add(product, quantity=quantity)

        scale = Scale(attribute_code='weight')
        self.assertEqual(1*3 + 2*4, scale.weigh_basket(basket))
