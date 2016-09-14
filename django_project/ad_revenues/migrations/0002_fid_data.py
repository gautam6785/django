# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ad_revenues', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='fid_data',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('assets', models.IntegerField(default=0)),
                ('status', models.CharField(default=b'', max_length=100)),
                ('fid', models.OneToOneField(null=True, to='ad_revenues.foreign_ids')),
            ],
        ),
    ]
