from django.views import generic
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.conf import settings

from oscar.core.loading import get_classes, get_model

from django_tables2 import SingleTableMixin

from oscar.views.generic import ObjectLookupView

(ChildProductForm,
 ProductForm,
 ProductClassSelectForm,
 ProductSearchForm,
 ProductClassForm,
 CategoryForm,
 StockRecordFormSet,
 StockAlertSearchForm,
 ProductCategoryFormSet,
 ProductImageFormSet,
 ProductRecommendationFormSet,
 ProductAttributesFormSet) \
    = get_classes('dashboard.catalogue.forms',
                  ('ChildProductForm',
                   'ProductForm',
                   'ProductClassSelectForm',
                   'ProductSearchForm',
                   'ProductClassForm',
                   'CategoryForm',
                   'StockRecordFormSet',
                   'StockAlertSearchForm',
                   'ProductCategoryFormSet',
                   'ProductImageFormSet',
                   'ProductRecommendationFormSet',
                   'ProductAttributesFormSet'))
ProductTable, CategoryTable \
    = get_classes('dashboard.catalogue.tables',
                  ('ProductTable', 'CategoryTable'))
ChildProduct = get_model('catalogue', 'ChildProduct')
Product = get_model('catalogue', 'Product')
Category = get_model('catalogue', 'Category')
ProductImage = get_model('catalogue', 'ProductImage')
ProductCategory = get_model('catalogue', 'ProductCategory')
ProductClass = get_model('catalogue', 'ProductClass')
StockRecord = get_model('partner', 'StockRecord')
StockAlert = get_model('partner', 'StockAlert')
Partner = get_model('partner', 'Partner')


def filter_products(queryset, user):
    """
    Restrict the queryset to products the given user has access to.
    A staff user is allowed to access all Products.
    A non-staff user is only allowed access to a product if they are in at
    least one stock record's partner user list.
    """
    if user.is_staff:
        return queryset

    if queryset.model == Product:
        filtered = queryset.filter(children__stockrecords__partner__users__pk=user.pk)

    elif queryset.model == ChildProduct:
        filtered = queryset.filter(stockrecords__partner__users__pk=user.pk)

    return filtered.distinct()


class ProductListView(SingleTableMixin, generic.TemplateView):
    """
    Dashboard view of the product list.
    Supports the permission-based dashboard.
    """

    template_name = 'dashboard/catalogue/product_list.html'
    form_class = ProductSearchForm
    productclass_form_class = ProductClassSelectForm
    table_class = ProductTable
    context_table_name = 'products'

    def get_context_data(self, **kwargs):
        ctx = super(ProductListView, self).get_context_data(**kwargs)
        ctx['form'] = self.form
        ctx['productclass_form'] = self.productclass_form_class()
        return ctx

    def get_description(self, form):
        if form.is_valid() and any(form.cleaned_data.values()):
            return _('Product search results')
        return _('Products')

    def get_table(self, **kwargs):
        if 'recently_edited' in self.request.GET:
            kwargs.update(dict(orderable=False))

        table = super(ProductListView, self).get_table(**kwargs)
        table.caption = self.get_description(self.form)
        return table

    def get_table_pagination(self):
        return dict(per_page=20)

    def filter_queryset(self, queryset):
        """
        Apply any filters to restrict the products that appear on the list
        """
        return filter_products(queryset, self.request.user)

    def get_queryset(self):
        """
        Build the queryset for this list
        """
        queryset = Product.objects.all()
        queryset = self.filter_queryset(queryset)
        queryset = self.apply_search(queryset)
        return queryset

    def apply_search(self, queryset):
        """
        Filter the queryset and set the description according to the search
        parameters given
        """
        self.form = self.form_class(self.request.GET)

        if not self.form.is_valid():
            return queryset

        data = self.form.cleaned_data

        if data.get('upc'):
            # Filter the queryset by upc
            # If there's an exact match, return it, otherwise return results
            # that contain the UPC
            matches_upc = Product.objects.filter(upc=data['upc'])
            qs_match = queryset.filter(
                Q(id=matches_upc.values('id')) |
                Q(id=matches_upc.values('parent_id')))

            if qs_match.exists():
                queryset = qs_match
            else:
                matches_upc = Product.objects.filter(upc__icontains=data['upc'])
                queryset = queryset.filter(
                    Q(id=matches_upc.values('id')) | Q(id=matches_upc.values('parent_id')))

        if data.get('title'):
            queryset = queryset.filter(title__icontains=data['title'])

        return queryset


class ProductCreateRedirectView(generic.RedirectView):
    permanent = False
    productclass_form_class = ProductClassSelectForm

    def get_product_create_url(self, product_class):
        """ Allow site to provide custom URL """
        return reverse('dashboard:catalogue-product-create',
                       kwargs={'product_class_slug': product_class.slug})

    def get_invalid_product_class_url(self):
        messages.error(self.request, _("Please choose a product type"))
        return reverse('dashboard:catalogue-product-list')

    def get_redirect_url(self, **kwargs):
        form = self.productclass_form_class(self.request.GET)
        if form.is_valid():
            product_class = form.cleaned_data['product_class']
            return self.get_product_create_url(product_class)

        else:
            return self.get_invalid_product_class_url()


class BaseProductCreateUpdateView(generic.UpdateView):
    context_object_name = 'product'
    parent = None
    product_class = None

    def get_queryset(self):
        """
        Filter products that the user doesn't have permission to update
        """
        return filter_products(self.model.objects.all(), self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super(BaseProductCreateUpdateView, self).get_context_data(**kwargs)
        ctx['product_class'] = self.product_class
        ctx['parent'] = self.parent
        ctx['title'] = self.get_page_title()

        for ctx_name, formset_class in self.formsets.items():
            if ctx_name not in ctx:
                ctx[ctx_name] = formset_class(product_class=self.product_class,
                                              user=self.request.user,
                                              instance=self.object)
        return ctx

    def get_form_kwargs(self):
        kwargs = super(BaseProductCreateUpdateView, self).get_form_kwargs()
        # For parent form
        if self.product_class is not None:
            kwargs['product_class'] = self.product_class
        # For child form
        if self.parent is not None:
            kwargs['parent'] = self.parent
        return kwargs

    def process_all_forms(self, form):
        """
        Short-circuits the regular logic to have one place to have our
        logic to check all forms
        """
        # Need to create the product here because the inline forms need it
        # can't use commit=False because ProductForm does not support it
        if self.creating and form.is_valid():
            self.object = form.save()

        formsets = {}
        for ctx_name, formset_class in self.formsets.items():
            formsets[ctx_name] = formset_class(self.request.POST,
                                               self.request.FILES,
                                               product_class=self.product_class,
                                               user=self.request.user,
                                               instance=self.object)

        is_valid = form.is_valid() and all([formset.is_valid()
                                            for formset in formsets.values()])

        cross_form_validation_result = self.clean(form, formsets)
        if is_valid and cross_form_validation_result:
            return self.forms_valid(form, formsets)
        else:
            return self.forms_invalid(form, formsets)

    # form_valid and form_invalid are called depending on the validation result
    # of just the product form and redisplay the form respectively return a
    # redirect to the success URL. In both cases we need to check our formsets
    # as well, so both methods do the same. process_all_forms then calls
    # forms_valid or forms_invalid respectively, which do the redisplay or
    # redirect.
    form_valid = form_invalid = process_all_forms

    def clean(self, form, formsets):
        """
        Perform any cross-form/formset validation. If there are errors, attach
        errors to a form or a form field so that they are displayed to the user
        and return False. If everything is valid, return True. This method will
        be called regardless of whether the individual forms are valid.
        """
        return True

    def forms_valid(self, form, formsets):
        """
        Save all changes and display a success url.
        When creating the first child product, this method also sets the new
        parent's structure accordingly.
        """
        self.object = form.save()

        # Save formsets
        for formset in formsets.values():
            formset.save()

        return HttpResponseRedirect(self.get_success_url())

    def forms_invalid(self, form, formsets):
        # delete the temporary product again
        if self.creating and self.object and self.object.pk is not None:
            self.object.delete()
            self.object = None

        messages.error(self.request,
                       _("Your submitted data was not valid - please "
                         "correct the errors below"))
        ctx = self.get_context_data(form=form, **formsets)
        return self.render_to_response(ctx)

    def get_url_with_querystring(self, url):
        url_parts = [url]
        if self.request.GET.urlencode():
            url_parts += [self.request.GET.urlencode()]
        return "?".join(url_parts)

    def get_success_url(self):
        """
        Renders a success message and redirects depending on the button:
        - Standard case is pressing "Save"; redirects to the product list
        - When "Save and continue" is pressed, we stay on the same page
        - When "Create (another) child product" is pressed, it redirects
          to a new product creation page
        """
        msg = render_to_string(
            self.message_template_name,
            {
                'product': self.object,
                'creating': self.creating,
                'request': self.request
            })
        messages.success(self.request, msg, extra_tags="safe noicon")

        action = self.request.POST.get('action')
        if action == 'continue':
            url = reverse(
                self.continue_pattern, kwargs={"pk": self.object.id})
        elif action == 'create-another-child' and self.parent:
            url = reverse(
                'dashboard:catalogue-product-create-child',
                kwargs={'parent_pk': self.parent.pk})
        elif action == 'create-child':
            url = reverse(
                'dashboard:catalogue-product-create-child',
                kwargs={'parent_pk': self.object.pk})
        else:
            url = reverse('dashboard:catalogue-product-list')
        return self.get_url_with_querystring(url)


class ChildProductCreateUpdateView(BaseProductCreateUpdateView):

    template_name = 'dashboard/catalogue/child_product_update.html'
    message_template_name = 'dashboard/catalogue/messages/child_product_saved.html'
    model = ChildProduct

    form_class = ChildProductForm
    stockrecord_formset = StockRecordFormSet

    continue_pattern = 'dashboard:catalogue-child-product'

    def __init__(self, *args, **kwargs):
        super(ChildProductCreateUpdateView, self).__init__(*args, **kwargs)
        self.formsets = {'stockrecord_formset': self.stockrecord_formset}

    def get_object(self, queryset=None):
        """
        This parts allows generic.UpdateView to handle creating products as
        well. The only distinction between an UpdateView and a CreateView
        is that self.object is None. We emulate this behavior.

        This method is also responsible for setting self.product_class and
        self.parent.
        """
        self.creating = 'pk' not in self.kwargs
        if self.creating:
            parent_pk = self.kwargs.get('parent_pk')
            self.parent = get_object_or_404(Product, pk=parent_pk)
            self.product_class = self.parent.product_class
        else:
            product = super(ChildProductCreateUpdateView, self).get_object(queryset)
            self.parent = product.parent
            self.product_class = self.parent.product_class
            return product

    def get_page_title(self):
        if self.creating:
            return _('Create new variant for %(parent)s') % {
                'parent': self.parent}
        else:
            return unicode(self.object)

class ProductCreateUpdateView(BaseProductCreateUpdateView):
    template_name = 'dashboard/catalogue/product_update.html'
    message_template_name = 'dashboard/catalogue/messages/product_saved.html'
    model = Product

    form_class = ProductForm
    category_formset = ProductCategoryFormSet
    image_formset = ProductImageFormSet
    recommendations_formset = ProductRecommendationFormSet

    continue_pattern = 'dashboard:catalogue-product'

    def __init__(self, *args, **kwargs):
        super(ProductCreateUpdateView, self).__init__(*args, **kwargs)
        self.formsets = {'category_formset': self.category_formset,
                         'image_formset': self.image_formset,
                         'recommended_formset': self.recommendations_formset}

    def get_object(self, queryset=None):
        """
        This parts allows generic.UpdateView to handle creating products as
        well. The only distinction between an UpdateView and a CreateView
        is that self.object is None. We emulate this behavior.
 
        This method is also responsible for setting self.product_class.
        """
        self.creating = 'pk' not in self.kwargs
        if self.creating:
            product_class_slug = self.kwargs.get('product_class_slug')
            self.product_class = get_object_or_404(
                ProductClass, slug=product_class_slug)
        else:
            product = super(ProductCreateUpdateView, self).get_object(queryset)
            self.product_class = product.product_class
            return product

    def get_page_title(self):
        if self.creating:
            return _('Create new %(product_class)s product') % {
                'product_class': self.product_class.name}
        else:
            return self.object.title

class BaseProductDeleteView(generic.DeleteView):
    """
    Dashboard view to delete a product. Has special logic for deleting the
    last child product.
    Supports the permission-based dashboard.
    """
    context_object_name = 'product'

    def get_queryset(self):
        """
        Filter products that the user doesn't have permission to update
        """
        return filter_products(self.model.objects.all(), self.request.user)
    
    def get_context_data(self, **kwargs):
        ctx = super(BaseProductDeleteView, self).get_context_data(**kwargs)
        ctx['title'] = self.title
        return ctx
    
    def post_success_message(self):
        msg = self.success_message % { 'title': self.object.get_title() }
        messages.success(self.request, msg)

class ChildProductDeleteView(BaseProductDeleteView):
    template_name = 'dashboard/catalogue/child_product_delete.html'
    model = ChildProduct
    title = _("Delete variant?")
    success_message = _("Deleted variant '%(title)s'")

    def get_success_url(self):
        """
        When deleting child products, this view redirects to editing the
        parent product. When deleting any other product, it redirects to the
        product list view.
        """
        self.post_success_message()
        return reverse('dashboard:catalogue-product', kwargs={'pk': self.object.parent.pk})

class ProductDeleteView(BaseProductDeleteView):
    template_name = 'dashboard/catalogue/product_delete.html'
    model = Product
    title = _("Delete product?")
    success_message = _("Deleted product '%(title)s'")

    def get_success_url(self):
        """
        When deleting child products, this view redirects to editing the
        parent product. When deleting any other product, it redirects to the
        product list view.
        """
        self.post_success_message()
        return reverse('dashboard:catalogue-product-list')


class StockAlertListView(generic.ListView):
    template_name = 'dashboard/catalogue/stockalert_list.html'
    model = StockAlert
    context_object_name = 'alerts'
    paginate_by = settings.OSCAR_STOCK_ALERTS_PER_PAGE

    def get_context_data(self, **kwargs):
        ctx = super(StockAlertListView, self).get_context_data(**kwargs)
        ctx['form'] = self.form
        ctx['description'] = self.description
        return ctx

    def get_queryset(self):
        if 'status' in self.request.GET:
            self.form = StockAlertSearchForm(self.request.GET)
            if self.form.is_valid():
                status = self.form.cleaned_data['status']
                self.description = _('Alerts with status "%s"') % status
                return self.model.objects.filter(status=status)
        else:
            self.description = _('All alerts')
            self.form = StockAlertSearchForm()
        return self.model.objects.all()


class CategoryListView(SingleTableMixin, generic.TemplateView):
    template_name = 'dashboard/catalogue/category_list.html'
    table_class = CategoryTable
    context_table_name = 'categories'

    def get_queryset(self):
        return Category.get_root_nodes()

    def get_context_data(self, *args, **kwargs):
        ctx = super(CategoryListView, self).get_context_data(*args, **kwargs)
        ctx['child_categories'] = Category.get_root_nodes()
        return ctx


class CategoryDetailListView(SingleTableMixin, generic.DetailView):
    template_name = 'dashboard/catalogue/category_list.html'
    model = Category
    context_object_name = 'category'
    table_class = CategoryTable
    context_table_name = 'categories'

    def get_table_data(self):
        return self.object.get_children()

    def get_context_data(self, *args, **kwargs):
        ctx = super(CategoryDetailListView, self).get_context_data(*args,
                                                                   **kwargs)
        ctx['child_categories'] = self.object.get_children()
        ctx['ancestors'] = self.object.get_ancestors_and_self()
        return ctx


class CategoryListMixin(object):

    def get_success_url(self):
        parent = self.object.get_parent()
        if parent is None:
            return reverse("dashboard:catalogue-category-list")
        else:
            return reverse("dashboard:catalogue-category-detail-list",
                           args=(parent.pk,))


class CategoryCreateView(CategoryListMixin, generic.CreateView):
    template_name = 'dashboard/catalogue/category_form.html'
    model = Category
    form_class = CategoryForm

    def get_context_data(self, **kwargs):
        ctx = super(CategoryCreateView, self).get_context_data(**kwargs)
        ctx['title'] = _("Add a new category")
        return ctx

    def get_success_url(self):
        messages.info(self.request, _("Category created successfully"))
        return super(CategoryCreateView, self).get_success_url()

    def get_initial(self):
        # set child category if set in the URL kwargs
        initial = super(CategoryCreateView, self).get_initial()
        if 'parent' in self.kwargs:
            initial['_ref_node_id'] = self.kwargs['parent']
        return initial


class CategoryUpdateView(CategoryListMixin, generic.UpdateView):
    template_name = 'dashboard/catalogue/category_form.html'
    model = Category
    form_class = CategoryForm

    def get_context_data(self, **kwargs):
        ctx = super(CategoryUpdateView, self).get_context_data(**kwargs)
        ctx['title'] = _("Update category '%s'") % self.object.name
        return ctx

    def get_success_url(self):
        messages.info(self.request, _("Category updated successfully"))
        return super(CategoryUpdateView, self).get_success_url()


class CategoryDeleteView(CategoryListMixin, generic.DeleteView):
    template_name = 'dashboard/catalogue/category_delete.html'
    model = Category

    def get_context_data(self, *args, **kwargs):
        ctx = super(CategoryDeleteView, self).get_context_data(*args, **kwargs)
        ctx['parent'] = self.object.get_parent()
        return ctx

    def get_success_url(self):
        messages.info(self.request, _("Category deleted successfully"))
        return super(CategoryDeleteView, self).get_success_url()


class ProductLookupView(ObjectLookupView):
    model = Product

    def get_queryset(self):
        return self.model.objects.all()

    def lookup_filter(self, qs, term):
        return qs.filter(Q(title__icontains=term)
                         | Q(parent__title__icontains=term))


class ProductClassCreateUpdateView(generic.UpdateView):

    template_name = 'dashboard/catalogue/product_class_form.html'
    model = ProductClass
    form_class = ProductClassForm
    product_attributes_formset = ProductAttributesFormSet

    def process_all_forms(self, form):
        """
        This validates both the ProductClass form and the
        ProductClassAttributes formset at once
        making it possible to display all their errors at once.
        """
        if self.creating and form.is_valid():
            # the object will be needed by the product_attributes_formset
            self.object = form.save(commit=False)

        attributes_formset = self.product_attributes_formset(
            self.request.POST, self.request.FILES, instance=self.object)

        is_valid = form.is_valid() and attributes_formset.is_valid()

        if is_valid:
            return self.forms_valid(form, attributes_formset)
        else:
            return self.forms_invalid(form, attributes_formset)

    def forms_valid(self, form, attributes_formset):
        form.save()
        attributes_formset.save()

        return HttpResponseRedirect(self.get_success_url())

    def forms_invalid(self, form, attributes_formset):
        messages.error(self.request,
                       _("Your submitted data was not valid - please "
                         "correct the errors below"
                         ))
        ctx = self.get_context_data(form=form,
                                    attributes_formset=attributes_formset)
        return self.render_to_response(ctx)

    form_valid = form_invalid = process_all_forms

    def get_context_data(self, *args, **kwargs):
        ctx = super(ProductClassCreateUpdateView, self).get_context_data(
            *args, **kwargs)

        if "attributes_formset" not in ctx:
            ctx["attributes_formset"] = self.product_attributes_formset(
                instance=self.object)

        ctx["title"] = self.get_title()

        return ctx


class ProductClassCreateView(ProductClassCreateUpdateView):

    creating = True

    def get_object(self):
        return None

    def get_title(self):
        return _("Add a new product type")

    def get_success_url(self):
        messages.info(self.request, _("Product type created successfully"))
        return reverse("dashboard:catalogue-class-list")


class ProductClassUpdateView(ProductClassCreateUpdateView):

    creating = False

    def get_title(self):
        return _("Update product type '%s'") % self.object.name

    def get_success_url(self):
        messages.info(self.request, _("Product type updated successfully"))
        return reverse("dashboard:catalogue-class-list")

    def get_object(self):
        product_class = get_object_or_404(ProductClass, pk=self.kwargs['pk'])
        return product_class


class ProductClassListView(generic.ListView):
    template_name = 'dashboard/catalogue/product_class_list.html'
    context_object_name = 'classes'
    model = ProductClass

    def get_context_data(self, *args, **kwargs):
        ctx = super(ProductClassListView, self).get_context_data(*args,
                                                                 **kwargs)
        ctx['title'] = _("Product Types")
        return ctx


class ProductClassDeleteView(generic.DeleteView):
    template_name = 'dashboard/catalogue/product_class_delete.html'
    model = ProductClass
    form_class = ProductClassForm

    def get_context_data(self, *args, **kwargs):
        ctx = super(ProductClassDeleteView, self).get_context_data(*args,
                                                                   **kwargs)
        ctx['title'] = _("Delete product type '%s'") % self.object.name
        product_count = self.object.products.count()

        if product_count > 0:
            ctx['disallow'] = True
            ctx['title'] = _("Unable to delete '%s'") % self.object.name
            messages.error(self.request,
                           _("%i products are still assigned to this type") %
                           product_count)
        return ctx

    def get_success_url(self):
        messages.info(self.request, _("Product type deleted successfully"))
        return reverse("dashboard:catalogue-class-list")
