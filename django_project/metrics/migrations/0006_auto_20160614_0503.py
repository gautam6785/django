# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('metrics', '0005_auto_20160405_0922'),
    ]

    operations = [
        migrations.AlterField(
            model_name='applereportrecord',
            name='country_code',
            field=models.ForeignKey(related_name='countries', db_column=b'country_code', to_field=b'alpha2', to='localization.Country'),
        ),
        migrations.AlterField(
            model_name='applereportrecord',
            name='customer_id',
            field=models.ForeignKey(to='customers.Customer', db_column=b'customer_id'),
        ),
        migrations.AlterField(
            model_name='googleinstallationreportrecord',
            name='customer_id',
            field=models.ForeignKey(to='customers.Customer', db_column=b'customer_id'),
        ),
        migrations.AlterField(
            model_name='googlereportrecord',
            name='customer_id',
            field=models.ForeignKey(to='customers.Customer', db_column=b'customer_id'),
        ),
    ]
