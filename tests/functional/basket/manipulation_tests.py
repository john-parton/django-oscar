from oscar.test.testcases import WebTestCase
from oscar.test import factories
from oscar.apps.basket import models


class TestAddingToBasket(WebTestCase):

    def test_works_for_standalone_product(self):
        parent, __, __ = factories.create_product_heirarchy(num_in_stock=10)

        detail_page = self.get(parent.get_absolute_url())
        response = detail_page.forms['add_to_basket_form'].submit()

        self.assertIsRedirect(response)
        baskets = models.Basket.objects.all()
        self.assertEqual(1, len(baskets))

        basket = baskets[0]
        self.assertEqual(1, basket.num_items)

    def test_works_for_child_product(self):
        parent = factories.ProductFactory()
        for __ in range(3):
            child = factories.ChildProductFactory(parent=parent)
            factories.StockRecordFactory(product=child)

        detail_page = self.get(parent.get_absolute_url())
        form = detail_page.forms['add_to_basket_form']
        # Select the last added child
        form['child'] = child.id
        response = form.submit()

        self.assertIsRedirect(response)
        baskets = models.Basket.objects.all()
        self.assertEqual(1, len(baskets))

        basket = baskets[0]
        self.assertEqual(1, basket.num_items)
