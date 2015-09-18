# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0002_auto_20140827_1705'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productrecord',
            name='product',
            field=models.OneToOneField(related_name='stats', verbose_name='Product', to='catalogue.ChildProduct'),
        ),
    ]
