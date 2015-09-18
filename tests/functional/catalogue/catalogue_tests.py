from django.conf import settings
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.utils.six.moves import http_client

from oscar.apps.catalogue.models import Category
from oscar.test.decorators import ignore_deprecation_warnings
from oscar.test.testcases import WebTestCase

from oscar.test.factories import create_product
from oscar.test import factories


class TestProductDetailView(WebTestCase):

    def test_enforces_canonical_url(self):
        p = create_product()
        kwargs = {'product_slug': '1_wrong-but-valid-slug_1',
                  'pk': p.id}
        wrong_url = reverse('catalogue:detail', kwargs=kwargs)

        response = self.app.get(wrong_url)
        self.assertEqual(http_client.MOVED_PERMANENTLY, response.status_code)
        self.assertTrue(p.get_absolute_url() in response.location)

    def test_child_to_parent_redirect(self):
        # Children no longer have their own pages and so cannot redirect to parents
        pass


class TestProductListView(WebTestCase):

    def test_shows_add_to_basket_button_for_available_product(self):
        product, __, __ = factories.create_product_heirarchy(num_in_stock=1)
        page = self.app.get(reverse('catalogue:index'))
        self.assertContains(page, product.title)
        self.assertContains(page, "Add to basket")

    def test_shows_not_available_for_out_of_stock_product(self):
        product, __, __ = factories.create_product_heirarchy(num_in_stock=0)

        page = self.app.get(reverse('catalogue:index'))

        self.assertContains(page, product.title)
        self.assertContains(page, "Unavailable")

    def test_shows_pagination_navigation_for_multiple_pages(self):
        per_page = settings.OSCAR_PRODUCTS_PER_PAGE
        title = u"Product #%d"
        for idx in range(0, int(1.5 * per_page)):
            factories.create_product_heirarchy(title=title % idx)

        page = self.app.get(reverse('catalogue:index'))

        self.assertContains(page, "Page 1 of 2")


class TestProductCategoryView(WebTestCase):

    def setUp(self):
        self.category = Category.add_root(name="Products")

    def test_browsing_works(self):
        correct_url = self.category.get_absolute_url()
        response = self.app.get(correct_url)
        self.assertEqual(http_client.OK, response.status_code)

    def test_enforces_canonical_url(self):
        kwargs = {'category_slug': '1_wrong-but-valid-slug_1',
                  'pk': self.category.pk}
        wrong_url = reverse('catalogue:category', kwargs=kwargs)

        response = self.app.get(wrong_url)
        self.assertEqual(http_client.MOVED_PERMANENTLY, response.status_code)
        self.assertTrue(self.category.get_absolute_url() in response.location)

    @ignore_deprecation_warnings
    def test_can_chop_off_last_part_of_url(self):
        # We cache category URLs, which normally is a safe thing to do, as
        # the primary key stays the same and ProductCategoryView only looks
        # at the key any way.
        # But this test chops the URLs, and hence relies on the URLs being
        # correct. So in this case, we start with a clean cache to ensure
        # our URLs are correct.
        cache.clear()

        child_category = self.category.add_child(name='Cool products')
        full_url = child_category.get_absolute_url()
        chopped_url = full_url.rsplit('/', 2)[0]
        parent_url = self.category.get_absolute_url()
        response = self.app.get(chopped_url).follow()  # fails if no redirect
        self.assertTrue(response.url.endswith(parent_url))
