from django.core.urlresolvers import reverse
from django.utils.six.moves import http_client

from oscar.core.loading import get_model
from oscar.test.testcases import WebTestCase, add_permissions
from oscar.test import factories
from oscar.test.factories import create_product
from oscar.test.factories import (
    CategoryFactory, PartnerFactory, ProductFactory, ProductAttributeFactory)

ChildProduct = get_model('catalogue', 'ChildProduct')
Product = get_model('catalogue', 'Product')
ProductClass = get_model('catalogue', 'ProductClass')
ProductCategory = get_model('catalogue', 'ProductCategory')
Category = get_model('catalogue', 'Category')
StockRecord = get_model('partner', 'stockrecord')


class TestCatalogueViews(WebTestCase):
    is_staff = True

    def test_exist(self):
        urls = [reverse('dashboard:catalogue-product-list'),
                reverse('dashboard:catalogue-category-list'),
                reverse('dashboard:stock-alert-list')]
        for url in urls:
            self.assertIsOk(self.get(url))


class TestAStaffUser(WebTestCase):
    is_staff = True

    def setUp(self):
        super(TestAStaffUser, self).setUp()
        self.partner = PartnerFactory()

    def test_can_create_a_product_without_stockrecord(self):
        category = CategoryFactory()
        product_class = ProductClass.objects.create(name="Book")
        page = self.get(reverse('dashboard:catalogue-product-create',
                                args=(product_class.slug,)))
        form = page.form
        form['title'] = 'new product'
        form['productcategory_set-0-category'] = category.id
        form.submit()

        self.assertEqual(Product.objects.count(), 1)

    def test_can_create_and_continue_editing_a_product(self):
        category = CategoryFactory()
        product_class = ProductClass.objects.create(name="Book")
        page = self.get(reverse('dashboard:catalogue-product-create',
                                args=(product_class.slug,)))
        form = page.form
        form['title'] = 'new product'
        form['productcategory_set-0-category'] = category.id
        page = form.submit(name='action', value='continue')

        self.assertEqual(Product.objects.count(), 1)
        product = Product.objects.all()[0]
        self.assertRedirects(page, reverse('dashboard:catalogue-product',
                                           kwargs={'pk': product.id}))

    def test_can_update_a_product_without_stockrecord(self):
        new_title = u'foobar'
        category = CategoryFactory()
        product = ProductFactory()

        page = self.get(
            reverse('dashboard:catalogue-product',
                    kwargs={'pk': product.id})
        )
        form = page.forms[0]
        form['productcategory_set-0-category'] = category.id
        assert form['title'].value != new_title
        form['title'] = new_title
        form.submit()

        try:
            product = Product.objects.get(pk=product.pk)
        except Product.DoesNotExist:
            pass
        else:
            self.assertTrue(product.title == new_title)

    def test_can_create_child_product_with_required_attributes(self):
        attribute = ProductAttributeFactory(required=True)
        product_class = attribute.product_class
        parent_product = ProductFactory(product_class=product_class)

        num_initial_child_products = ChildProduct.objects.count()

        url = reverse(
            'dashboard:catalogue-product-create-child',
            kwargs={'parent_pk': parent_product.pk})
        page = self.get(url)

        form = page.form
        form['upc'] = '123456'
        form['title'] = 'new product'
        form['attr_weight'] = '5'
        form.submit()

        self.assertEqual(ChildProduct.objects.count(), num_initial_child_products+1)

    def test_can_delete_a_standalone_product(self):
        product = create_product(partner_users=[self.user])
        category = Category.add_root(name='Test Category')
        ProductCategory.objects.create(category=category, product=product)

        page = self.get(reverse('dashboard:catalogue-product-delete',
                                args=(product.id,))).form.submit()

        self.assertRedirects(page, reverse('dashboard:catalogue-product-list'))
        self.assertEqual(Product.objects.count(), 0)
        self.assertEqual(StockRecord.objects.count(), 0)
        self.assertEqual(Category.objects.count(), 1)
        self.assertEqual(ProductCategory.objects.count(), 0)

    def test_can_delete_a_parent_product(self):
        parent_product = factories.ProductFactory()

        url = reverse(
            'dashboard:catalogue-product-delete',
            args=(parent_product.id,))
        page = self.get(url).form.submit()

        self.assertRedirects(page, reverse('dashboard:catalogue-product-list'))
        self.assertEqual(Product.objects.count(), 0)

    def test_can_delete_a_child_product(self):
        parent_product, child_product, __ = factories.create_product_heirarchy()

        url = reverse(
            'dashboard:catalogue-child-product-delete',
            args=(child_product.id,))
        page = self.get(url).form.submit()

        expected_url = reverse(
            'dashboard:catalogue-product', kwargs={'pk': parent_product.pk})
        self.assertRedirects(page, expected_url)
        self.assertEqual(ChildProduct.objects.count(), 0)

    def test_can_list_her_products(self):
        product1 = create_product(partner_users=[self.user, ])
        product2 = create_product(partner_name="sneaky", partner_users=[])
        page = self.get(reverse('dashboard:catalogue-product-list'))
        products_on_page = [row.record for row
                            in page.context['products'].page.object_list]
        assert product1 in products_on_page
        assert product2 in products_on_page

    def test_can_create_a_child_product(self):
        parent_product = create_product()
        url = reverse(
            'dashboard:catalogue-product-create-child',
            kwargs={'parent_pk': parent_product.pk})
        form = self.get(url).form
        form.submit()

        self.assertEqual(ChildProduct.objects.count(), 1)


class TestANonStaffUser(TestAStaffUser):
    is_staff = False
    is_anonymous = False
    permissions = ['partner.dashboard_access', ]

    def setUp(self):
        super(TestANonStaffUser, self).setUp()
        add_permissions(self.user, self.permissions)
        self.partner.users.add(self.user)

    def test_can_list_her_products(self):
        product1 = create_product(partner_name="A", partner_users=[self.user])
        product2 = create_product(partner_name="B", partner_users=[])
        page = self.get(reverse('dashboard:catalogue-product-list'))
        products_on_page = [row.record for row
                            in page.context['products'].page.object_list]
        assert product1 in products_on_page
        assert product2 not in products_on_page

    def test_cant_create_a_child_product(self):
        parent_product = create_product(structure='parent')
        url = reverse(
            'dashboard:catalogue-product-create-child',
            kwargs={'parent_pk': parent_product.pk})
        response = self.get(url, status='*')
        self.assertEqual(http_client.FORBIDDEN, response.status_code)

    # Tests below can't work because they don't create a stockrecord

    def test_can_create_a_product_without_stockrecord(self):
        pass

    def test_can_update_a_product_without_stockrecord(self):
        pass

    def test_can_create_product_with_required_attributes(self):
        pass

    # Tests below can't work because child products aren't supported with the
    # permission-based dashboard

    def test_can_delete_a_child_product(self):
        pass

    def test_can_delete_a_parent_product(self):
        pass

    def test_can_create_a_child_product(self):
        pass

    def test_cant_create_child_product_for_invalid_parents(self):
        pass
