# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import oscar.models.fields
import oscar.core.validators
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0005_auto_20150604_1450'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChildProduct',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('upc', oscar.models.fields.NullCharField(max_length=64, help_text='Universal Product Code (UPC) is an identifier for a product which is not specific to a particular  supplier. Eg an ISBN for a book.', unique=True, verbose_name='UPC')),
                ('title', models.CharField(max_length=255, verbose_name='Title', blank=True)),
                ('slug', models.SlugField(max_length=255, verbose_name='Slug')),
                ('description', models.TextField(verbose_name='Description', blank=True)),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='Date created')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date updated', db_index=True)),
            ],
            options={
                'ordering': ['-date_created'],
                'abstract': False,
                'verbose_name': 'Child product',
                'verbose_name_plural': 'Child products',
            },
        ),
        migrations.AlterModelOptions(
            name='product',
            options={'ordering': ['-date_created'], 'verbose_name': 'Parent product', 'verbose_name_plural': 'Parent products'},
        ),
        migrations.RemoveField(
            model_name='product',
            name='attributes',
        ),
        migrations.RemoveField(
            model_name='product',
            name='parent',
        ),
        migrations.RemoveField(
            model_name='product',
            name='structure',
        ),
        migrations.RemoveField(
            model_name='product',
            name='upc',
        ),
        migrations.AlterField(
            model_name='product',
            name='product_class',
            field=models.ForeignKey(related_name='products', on_delete=django.db.models.deletion.PROTECT, verbose_name='Product type', to='catalogue.ProductClass', help_text='Choose what type of product this is'),
        ),
        migrations.AlterField(
            model_name='product',
            name='title',
            field=models.CharField(max_length=255, verbose_name='Title'),
        ),
        migrations.AlterField(
            model_name='productattribute',
            name='code',
            field=models.SlugField(max_length=128, verbose_name='Code', validators=[django.core.validators.RegexValidator(regex=b'^[a-zA-Z_][0-9a-zA-Z_]*$', message="Code can only contain the letters a-z, A-Z, digits, and underscores, and can't start with a digit"), oscar.core.validators.non_python_keyword]),
        ),
        migrations.AlterField(
            model_name='productattributevalue',
            name='product',
            field=models.ForeignKey(related_name='attribute_values', verbose_name='Product', to='catalogue.ChildProduct'),
        ),
        migrations.AddField(
            model_name='childproduct',
            name='attributes',
            field=models.ManyToManyField(help_text='A product attribute is something that this product may have, such as a size, as specified by its class', to='catalogue.ProductAttribute', verbose_name='Attributes', through='catalogue.ProductAttributeValue'),
        ),
        migrations.AddField(
            model_name='childproduct',
            name='parent',
            field=models.ForeignKey(related_name='children', verbose_name='Parent product', to='catalogue.Product', help_text="Only choose a parent product if you're creating a child product.  For example if this is a size 4 of a particular t-shirt.  Leave blank if this is a stand-alone product (i.e. there is only one version of this product)."),
        ),
    ]
