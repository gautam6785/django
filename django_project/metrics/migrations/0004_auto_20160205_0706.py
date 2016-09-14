# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import core.customfields

class Migration(migrations.Migration):

    dependencies = [
        ('metrics', '0003_auto_20151228_0533'),
    ]

    operations = [
		migrations.CreateModel(
            name='GoogleInstallationReportRecord',
            fields=[
                ('creation_time', models.DateTimeField(auto_now_add=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('record_id', core.customfields.BigAutoField(serialize=False, primary_key=True)),
                ('customer_id', models.ForeignKey(db_column=b'customer_id', to='customers.Customer', null=True, db_index=True)),
                ('date', models.DateField()),
                ('package_name', models.CharField(max_length=256, db_index=True)),
                ('country', models.CharField(max_length=256, null=True)),
                ('current_device_installs', models.IntegerField()),
                ('daily_device_installs', models.IntegerField()),
                ('daily_device_uninstalls', models.IntegerField()),
                ('daily_device_upgrades', models.IntegerField()),
                ('current_user_installs', models.IntegerField()),
                ('total_user_installs', models.IntegerField()),
                ('daily_user_installs', models.IntegerField()),
                ('daily_user_uninstalls', models.IntegerField()),
            ],
            options={
                'db_table': 'google_installation_report_records',
            },
            bases=(models.Model,),
        ),
    ]
