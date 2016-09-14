# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ad_revenues', '0009_adcolony_credentials'),
    ]

    operations = [
        migrations.CreateModel(
            name='inmobi_credentials',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('email', models.CharField(max_length=200, null=True)),
                ('password', models.CharField(max_length=256, null=True)),
                ('api_key', models.CharField(max_length=50, null=True)),
                ('account_id', models.CharField(max_length=100, null=True)),
                ('session_id', models.CharField(max_length=100, null=True)),
            ],
        ),
    ]
