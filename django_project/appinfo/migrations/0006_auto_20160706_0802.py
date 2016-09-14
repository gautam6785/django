# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import core.customfields


class Migration(migrations.Migration):

    dependencies = [
        ('appinfo', '0005_auto_20160616_1300'),
    ]

    operations = [
		migrations.AddField(
            model_name='appinfo',
            name='sku',
            field=models.CharField(max_length=256, null=True),
            preserve_default=True,
        ),
    ]
