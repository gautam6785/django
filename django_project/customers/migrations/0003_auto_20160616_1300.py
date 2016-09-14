# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0002_auto_20160614_0503'),
    ]

    operations = [
		migrations.AddField(
            model_name='customerexternallogininfo',
            name='display_name',
            field=models.CharField(max_length=256, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='customerexternallogininfo',
            name='latest_report',
            field=models.DateTimeField(null=True),
            preserve_default=True,
        ),
    ]
