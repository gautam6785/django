# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import core.customfields
from customers.models import Customer, CustomerExternalLoginInfo

class Migration(migrations.Migration):

    dependencies = [
        ('appinfo', '0004_auto_20160614_0457'),
    ]

    operations = [
		migrations.AddField(
            model_name='appinfo',
            name='customer_account_id',
            field=models.ForeignKey(CustomerExternalLoginInfo, db_column="customer_account_id", null=True, db_index=True),
            preserve_default=True,
        ),
    ]
