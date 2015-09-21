from django.test import TestCase

from oscar.apps.dashboard.ranges import forms
from oscar.test.factories import create_product
from oscar.apps.offer.models import Range
from oscar.test import factories


class RangeProductFormTests(TestCase):

    def setUp(self):
        self.range = Range.objects.create(name='dummy')

    def tearDown(self):
        Range.objects.all().delete()

    def submit_form(self, data):
        return forms.RangeProductForm(self.range, data)

    def test_either_query_or_file_must_be_submitted(self):
        form = self.submit_form({'query': ''})
        self.assertFalse(form.is_valid())

    def test_non_match_becomes_error(self):
        form = self.submit_form({'query': '123123'})
        self.assertFalse(form.is_valid())

    def test_matching_query_is_valid(self):
        factories.create_product_heirarchy(partner_sku='123123')
        form = self.submit_form({'query': '123123'})
        self.assertTrue(form.is_valid())

    def test_passing_form_return_product_list(self):
        parent, __, __ = factories.create_product_heirarchy(partner_sku='123123')
        form = self.submit_form({'query': '123123'})
        form.is_valid()
        self.assertEqual(1, len(form.get_products()))
        self.assertEqual(parent.id, form.get_products()[0].id)

    def test_missing_skus_are_available(self):
        factories.create_product_heirarchy(partner_sku='123123')
        form = self.submit_form({'query': '123123, 123xxx'})
        form.is_valid()
        self.assertEqual(1, len(form.get_missing_skus()))
        self.assertTrue('123xxx' in form.get_missing_skus())

    def test_only_dupes_is_invalid(self):
        parent, __, __ = factories.create_product_heirarchy(partner_sku='123123')
        self.range.add_product(parent)
        form = self.submit_form({'query': '123123'})
        self.assertFalse(form.is_valid())

    def test_dupe_skus_are_available(self):
        parent, __, __ = factories.create_product_heirarchy(partner_sku='123123')
        self.range.add_product(parent)
        form = self.submit_form({'query': '123123, 123124'})
        form.is_valid()
        self.assertFalse(form.is_valid())
        self.assertTrue('123123' in form.get_duplicate_skus())
