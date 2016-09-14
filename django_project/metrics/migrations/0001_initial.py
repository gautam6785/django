# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import core.customfields

class Migration(migrations.Migration):

    dependencies = [
		('customers', '0001_initial'),
    ]

    operations = [
		migrations.CreateModel(
            name='GoogleReportRecord',
            fields=[
                ('creation_time', models.DateTimeField(auto_now_add=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('record_id', core.customfields.BigAutoField(serialize=False, primary_key=True)),
                ('customer_id', models.ForeignKey(db_column=b'customer_id', to='customers.Customer', null=True, db_index=True)),
                ('order_number', models.CharField(max_length=255, db_index=True)),
                ('charged_date', models.DateField()),
                ('charged_time', models.DateTimeField()),
                ('financial_status', models.CharField(max_length=100)),
                ('device_model', models.CharField(max_length=100, null=True)),
                ('product_title', models.CharField(max_length=600)),
                ('product_id', models.CharField(max_length=256, db_index=True)),
                ('product_type', models.CharField(max_length=100)),
                ('sku_id', models.CharField(max_length=256, null=True)),
                ('sale_currency', models.CharField(max_length=10)),
                ('item_price', models.DecimalField(max_digits=30, decimal_places=10)),
                ('taxes', models.DecimalField(max_digits=30, decimal_places=10)),
                ('charged_amount', models.DecimalField(max_digits=30, decimal_places=10)),
                ('developer_proceeds', models.DecimalField(max_digits=30, decimal_places=10)),
                ('developer_proceeds_usd', models.DecimalField(max_digits=30, decimal_places=10)),
                ('buyer_city', models.CharField(max_length=256, null=True)),
                ('buyer_state', models.CharField(max_length=256, null=True)),
                ('buyer_postal_code', models.CharField(max_length=256, null=True)),
                ('buyer_country', models.CharField(max_length=256, null=True)),
            ],
            options={
                'db_table': 'google_report_records',
            },
            bases=(models.Model,),
        ),
    ]
