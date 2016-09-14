# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('metrics', '0002_auto_20151225_0948'),
    ]

    operations = [
		migrations.AddField(
            model_name='GoogleReportRecord',
            name='google_fee',
            field=models.DecimalField(max_digits=30, decimal_places=10, null=True),
        ),
        migrations.AddField(
            model_name='GoogleReportRecord',
            name='currency_conversion_rate',
            field=models.DecimalField(max_digits=30, decimal_places=10, null=True),
        ),
        migrations.AddField(
            model_name='GoogleReportRecord',
            name='merchant_currency',
            field=models.CharField(max_length=10, null=True),
        ),
        migrations.AddField(
            model_name='GoogleReportRecord',
            name='amount_merchant_currency',
            field=models.DecimalField(max_digits=30, decimal_places=10, null=True),
        ),
    ]
