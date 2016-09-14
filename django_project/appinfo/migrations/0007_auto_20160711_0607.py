# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appinfo', '0006_auto_20160706_0802'),
    ]

    operations = [
		migrations.AddField(
            model_name='appinfo',
            name='total_downloads',
            field=models.BigIntegerField(null=True, default=0),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='appinfo',
            name='total_revenue',
            field=models.DecimalField(max_digits=30, decimal_places=10, null=True, default=0),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='appinfo',
            name='iap_revenue',
            field=models.DecimalField(max_digits=30, decimal_places=10, null=True, default=0),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='appinfo',
            name='ad_revenue',
            field=models.DecimalField(max_digits=30, decimal_places=10, null=True, default=0),
            preserve_default=True,
        ),
    ]
