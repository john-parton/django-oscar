# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('basket', '0005_auto_20150604_1450'),
    ]

    operations = [
        migrations.AlterField(
            model_name='line',
            name='product',
            field=models.ForeignKey(related_name='basket_lines', verbose_name='Child product', to='catalogue.ChildProduct'),
        ),
    ]
