from __future__ import unicode_literals

from django.core.urlresolvers import reverse

from oscar.test import factories
from oscar.test.testcases import WebTestCase
from oscar.core.compat import get_user_model
from oscar.apps.catalogue.models import ChildProduct, Product
from oscar.apps.dashboard.catalogue.forms import ProductForm
from oscar.test.factories import (CategoryFactory, ProductClassFactory)

User = get_user_model()


class ProductWebTest(WebTestCase):
    is_staff = True

    def setUp(self):
        self.user = User.objects.create_user(username='testuser',
                                             email='test@email.com',
                                             password='somefancypassword')
        self.user.is_staff = self.is_staff
        self.user.save()

    def get(self, url, **kwargs):
        kwargs['user'] = self.user
        return self.app.get(url, **kwargs)


class TestGatewayPage(ProductWebTest):
    is_staff = True

    def test_redirects_to_list_page_when_no_query_param(self):
        url = reverse('dashboard:catalogue-product-create')
        response = self.get(url)
        self.assertRedirects(response,
                             reverse('dashboard:catalogue-product-list'))

    def test_redirects_to_list_page_when_invalid_query_param(self):
        url = reverse('dashboard:catalogue-product-create')
        response = self.get(url + '?product_class=bad')
        self.assertRedirects(response,
                             reverse('dashboard:catalogue-product-list'))

    def test_redirects_to_form_page_when_valid_query_param(self):
        pclass = ProductClassFactory(name='Books', slug='books')
        url = reverse('dashboard:catalogue-product-create')
        response = self.get(url + '?product_class=%s' % pclass.pk)
        expected_url = reverse('dashboard:catalogue-product-create',
                               kwargs={'product_class_slug': pclass.slug})
        self.assertRedirects(response, expected_url)


class TestCreateParentProduct(ProductWebTest):
    is_staff = True

    def setUp(self):
        self.pclass = ProductClassFactory(name='Books', slug='books')
        super(TestCreateParentProduct, self).setUp()

    def submit(self, title=None, category=None):
        url = reverse('dashboard:catalogue-product-create',
                      kwargs={'product_class_slug': self.pclass.slug})

        product_form = self.get(url).form

        product_form['title'] = title

        if category:
            product_form['productcategory_set-0-category'] = category.id

        return product_form.submit()

    def test_title_is_required(self):
        form = ProductForm({'title': ''}, product_class=self.pclass)

        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['title'], ['This field is required.'])

    def test_requires_a_category(self):
        response = self.submit(title="Nice T-Shirt")
        self.assertContains(response,
            "must have at least one category")
        self.assertEqual(Product.objects.count(), 0)

    def test_for_smoke(self):
        category = CategoryFactory()
        response = self.submit(title='testing', category=category)
        self.assertIsRedirect(response)
        self.assertEqual(Product.objects.count(), 1)


class TestCreateChildProduct(ProductWebTest):
    is_staff = True

    def test_disallow_duplicate_upc(self):
        parent, child1, __ = factories.create_product_heirarchy()
        child1.upc = '12345'
        child1.title = 'Nice T-Shirt'
        child1.save() 

        url = reverse('dashboard:catalogue-child-product-create',
                      kwargs={'parent_pk':parent.pk})

        child_product_form = self.get(url).form

        child_product_form['upc'] = '12345'
        child_product_form['title'] = 'Another Nice T-Shirt'

        response = child_product_form.submit()

        self.assertEqual(ChildProduct.objects.count(), 1)
        self.assertEqual(ChildProduct.objects.get(upc='12345').title, 'Nice T-Shirt')
        self.assertContains(response,
                            "Product with this UPC already exists.")


class TestProductUpdate(ProductWebTest):

    def test_product_update_form(self):
        self.product = factories.ProductFactory()
        url = reverse('dashboard:catalogue-product',
                      kwargs={'pk': self.product.id})

        page = self.get(url)
        product_form = page.form
        product_form['title'] = expected_title = 'Nice T-Shirt'
        page = product_form.submit()

        product = Product.objects.get(id=self.product.id)

        self.assertEqual(page.context['product'], self.product)
        self.assertEqual(product.title, expected_title)
