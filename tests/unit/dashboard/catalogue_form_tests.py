from django.test import TestCase

from oscar.apps.dashboard.catalogue import forms
from oscar.test import factories


class TestCreateProductForm(TestCase):

    def setUp(self):
        self.product_class = factories.ProductClassFactory()

    def submit(self, data):
        return forms.ProductForm(product_class=self.product_class, data=data)

    def test_validates_that_parent_products_must_have_title(self):
        form = self.submit({})
        self.assertFalse(form.is_valid())
        form = self.submit({'title': 'foo'})
        self.assertTrue(form.is_valid())


class TestCreateChildForm(TestCase):

    def setUp(self):
        self.product_class = factories.ProductClassFactory()
        self.parent = factories.ProductFactory(product_class=self.product_class)
    
    def submit(self, data):
        return forms.ChildProductForm(product_class=self.product_class, parent=self.parent, data=data)

    def test_validates_that_child_products_dont_need_a_title(self):
        form = self.submit({})
        self.assertTrue(form.is_valid())


class TestCreateProductAttributeForm(TestCase):

    def test_can_create_without_code(self):
        form = forms.ProductAttributesForm(data={
            "name": "Attr",
            "type": "text"
        })

        self.assertTrue(form.is_valid())

        product_attribute = form.save()

        # check that code is not None or empty string
        self.assertTrue(product_attribute.code)
