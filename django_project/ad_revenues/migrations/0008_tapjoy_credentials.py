# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ad_revenues', '0007_vungle_credentials'),
    ]

    operations = [
        migrations.CreateModel(
            name='tapjoy_credentials',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('email', models.CharField(max_length=200, null=True)),
                ('api_key', models.CharField(max_length=50, null=True)),
            ],
        ),
    ]
