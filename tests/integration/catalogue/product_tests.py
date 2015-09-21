# coding=utf-8
from django.db import IntegrityError
from django.test import TestCase
from django.core.exceptions import ValidationError

from oscar.apps.catalogue.models import (ChildProduct, Product, ProductClass, AttributeOption)
from oscar.test import factories
from oscar.test.decorators import ignore_deprecation_warnings


class ProductTests(TestCase):

    def setUp(self):
        self.product_class, _ = ProductClass.objects.get_or_create(
            name='Clothing')


class TopLevelProductTests(ProductTests):

    def test_top_level_products_must_have_product_class(self):
        product = Product(title=u"Kopfhörer")
        self.assertRaises(IntegrityError, product.save)


class ChildProductTests(ProductTests):

    def setUp(self):
        super(ChildProductTests, self).setUp()
        self.parent = Product.objects.create(
            title="Parent product",
            product_class=self.product_class,
            is_discountable=False)

    def test_create_child_products_with_attributes(self):
        product = ChildProduct(parent=self.parent, upc='1234', title='testing')
        product.attr.num_pages = 100
        product.save()

    def test_none_upc_is_represented_as_empty_string(self):
        product = ChildProduct(title='testing')
        self.assertEqual(product.upc, u'')

    def test_upc_uniqueness_enforced(self):
        ChildProduct.objects.create(parent=self.parent, title='testing', upc='bah')
        self.assertRaises(IntegrityError, ChildProduct.objects.create,
                          parent=self.parent, title='testing', upc='bah')

    def test_allow_two_child_products_without_upc(self):
        for __ in range(2):
            ChildProduct.objects.create(parent=self.parent, title='testing', upc=None)

    def test_child_products_dont_need_titles(self):
        ChildProduct.objects.create(parent=self.parent, title='')


class ProductAttributeCreationTests(TestCase):

    def test_validating_option_attribute(self):
        option_group = factories.AttributeOptionGroupFactory()
        option_1 = factories.AttributeOptionFactory(group=option_group)
        option_2 = factories.AttributeOptionFactory(group=option_group)
        pa = factories.ProductAttribute(
            type='option', option_group=option_group)

        self.assertRaises(ValidationError, pa.validate_value, 'invalid')
        pa.validate_value(option_1)
        pa.validate_value(option_2)

        invalid_option = AttributeOption(option='invalid option')
        self.assertRaises(
            ValidationError, pa.validate_value, invalid_option)

    def test_entity_attributes(self):
        unrelated_object = factories.PartnerFactory()
        attribute = factories.ProductAttributeFactory(type='entity')
        
        __, product, __ = factories.create_product_heirarchy()

        attribute_value = factories.ProductAttributeValueFactory(
            product=product, attribute=attribute, value_entity=unrelated_object)

        self.assertEqual(attribute_value.value, unrelated_object)
