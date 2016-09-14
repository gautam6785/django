# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import core.customfields

class Migration(migrations.Migration):

    dependencies = [
        ('metrics', '0004_auto_20160205_0706'),
        ('customers', '0001_initial'),
    ]

    operations = [
		migrations.CreateModel(
            name='AppleReportRecord',
            fields=[
                ('creation_time', models.DateTimeField(auto_now_add=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('record_id', core.customfields.BigAutoField(serialize=False, primary_key=True)),
                ('customer_id', models.ForeignKey(db_column=b'customer_id', to='customers.Customer', null=True, db_index=True)),
                ('apple_identifier', models.BigIntegerField(db_index=True)),
                ('provider', models.CharField(max_length=10)),
                ('provider_country', models.CharField(max_length=10)),
                ('sku', models.CharField(max_length=100)),
                ('developer', models.CharField(max_length=4000, null=True)),
                ('title', models.CharField(max_length=600)),
                ('version', models.CharField(max_length=100, null=True)),
                ('product_type_identifier', models.CharField(max_length=20)),
                ('units', models.DecimalField(max_digits=20, decimal_places=2)),
                ('developer_proceeds', models.DecimalField(max_digits=20, decimal_places=2)),
                ('developer_proceeds_usd', models.DecimalField(max_digits=30, decimal_places=10)),
                ('begin_date', models.DateField()),
                ('end_date', models.DateField()),
                ('customer_currency', models.CharField(max_length=10)),
                ('country_code', models.CharField(max_length=10)),
                ('currency_of_proceeds', models.CharField(max_length=10)),
                ('customer_price', models.DecimalField(max_digits=20, decimal_places=2)),
                ('promo_code', models.CharField(max_length=10, null=True)),
                ('parent_identifier', models.CharField(max_length=100, null=True)),
                ('subscription', models.CharField(max_length=10, null=True)),
                ('period', models.CharField(max_length=30, null=True)),
                ('category', models.CharField(max_length=50)),
                ('cmb', models.CharField(max_length=5, null=True)),
                ('device', models.CharField(max_length=600, null=True)),
                ('supported_platforms', models.CharField(max_length=600, null=True)),
            ],
            options={
                'db_table': 'apple_report_records',
            },
            bases=(models.Model,),
        ),
    ]
