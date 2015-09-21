import re

from django import forms
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from oscar.core.loading import get_model

Product = get_model('catalogue', 'Product')
Range = get_model('offer', 'Range')


class RangeForm(forms.ModelForm):

    class Meta:
        model = Range
        fields = [
            'name', 'description', 'is_public',
            'includes_all_products', 'included_categories'
        ]


class RangeProductForm(forms.Form):
    query = forms.CharField(
        max_length=1024, label=_("Product SKUs or UPCs"),
        widget=forms.Textarea, required=False,
        help_text=_("You can paste in a selection of SKUs or UPCs"))
    file_upload = forms.FileField(
        label=_("File of SKUs or UPCs"), required=False, max_length=255,
        help_text=_('Either comma-separated, or one identifier per line'))

    def __init__(self, range, *args, **kwargs):
        self.range = range
        super(RangeProductForm, self).__init__(*args, **kwargs)

    def clean(self):
        clean_data = super(RangeProductForm, self).clean()
        if not clean_data.get('query') and not clean_data.get('file_upload'):
            raise forms.ValidationError(
                _("You must submit either a list of SKU/UPCs or a file"))
        return clean_data

    def clean_query(self):
        raw = self.cleaned_data['query']
        if not raw:
            return raw

        # Check that the search matches some products
        ids = set(re.compile(r'[\w-]+').findall(raw))

        products = self.range.included_products.all()

        existing_ids = set()

        for sku, upc in products.values_list('children__stockrecords__partner_sku', 
                                             'children__upc').order_by().distinct():
            if sku:
                existing_ids.add(sku)
            if upc:
                existing_ids.add(upc)

        new_ids = ids - existing_ids

        self.duplicate_skus = existing_ids.intersection(ids)

        if len(new_ids) == 0:
            raise forms.ValidationError(
                _("The products with SKUs or UPCs matching %s are already in"
                  " this range") % (', '.join(ids)))

        self.products = Product.objects.filter(
            Q(children__stockrecords__partner_sku__in=new_ids) |
            Q(children__upc__in=new_ids))
        if len(self.products) == 0:
            raise forms.ValidationError(
                _("No products exist with a SKU or UPC matching %s")
                % ", ".join(ids))

        found_skus = set(self.products.values_list(
            'children__stockrecords__partner_sku', flat=True))
        found_upcs = set(self.products.values_list('children__upc', flat=True))
        found_ids = found_skus.union(found_upcs)
        self.missing_skus = new_ids - found_ids

        return raw

    def get_products(self):
        return self.products if hasattr(self, 'products') else []

    def get_missing_skus(self):
        return self.missing_skus

    def get_duplicate_skus(self):
        return self.duplicate_skus
