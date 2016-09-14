# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import core.customfields


class Migration(migrations.Migration):

    dependencies = [
        ('appinfo', '0002_auto_20160407_1329'),
    ]

    operations = [
        migrations.CreateModel(
            name='Currency',
            fields=[
                ('iso_code', models.CharField(max_length=3, serialize=False, primary_key=True)),
                ('symbol', models.CharField(max_length=3)),
                ('uni_code', models.CharField(max_length=8)),
                ('position', models.CharField(max_length=6)),
                ('comments', models.CharField(max_length=255)),
            ],
            options={
                'db_table': 'currencies',
                'verbose_name': 'currency',
                'verbose_name_plural': 'currencies',
            },
        ),
        migrations.AlterField(
            model_name='appinfo',
            name='has_iap',
            field=core.customfields.BigIntegerField(default=0, null=True),
        ),
        migrations.AlterField(
            model_name='appinfo',
            name='rating1',
            field=core.customfields.BigIntegerField(default=0, null=True),
        ),
        migrations.AlterField(
            model_name='appinfo',
            name='rating2',
            field=core.customfields.BigIntegerField(default=0, null=True),
        ),
        migrations.AlterField(
            model_name='appinfo',
            name='rating3',
            field=core.customfields.BigIntegerField(default=0, null=True),
        ),
        migrations.AlterField(
            model_name='appinfo',
            name='rating4',
            field=core.customfields.BigIntegerField(default=0, null=True),
        ),
        migrations.AlterField(
            model_name='appinfo',
            name='rating5',
            field=core.customfields.BigIntegerField(default=0, null=True),
        ),
        migrations.AlterField(
            model_name='appscreenshot',
            name='app_info_id',
            field=models.ForeignKey(db_column=b'app_info_id', to='appinfo.AppInfo', null=True),
        ),
        migrations.AlterField(
            model_name='appscreenshot',
            name='app_screenshot_id',
            field=core.customfields.BigAutoField(serialize=False, primary_key=True),
        ),
    ]
