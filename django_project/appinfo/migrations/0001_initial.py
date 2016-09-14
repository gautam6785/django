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
			name='PlatformType',
			fields=[
				('creation_time', models.DateTimeField(auto_now_add=True)),
				('last_modified', models.DateTimeField(auto_now=True)),
				('platform_type_id', models.AutoField(serialize=False, primary_key=True)),
				('platform_type_str', models.CharField(unique=True, max_length=255, choices=[(b'Android', b'Android'), (b'iOS', b'iOS'), (b'Web', b'Web')])),
				('description', models.CharField(max_length=512)),
			],
			options={
				'db_table': 'platform_types',
			},
			bases=(models.Model,),
		),
		
        migrations.CreateModel(
            name='AppInfo',
            fields=[
                ('app_info_id', core.customfields.BigAutoField(serialize=False, primary_key=True)),
                ('customer_id', models.ForeignKey(db_column=b'customer_id', to='customers.Customer', null=True, db_index=True)),
                ('app', models.CharField(max_length=256, db_index=True)),
                ('name', models.CharField(max_length=256, null=True)),
                ('identifier', core.customfields.BigIntegerField(null=True)),
                ('artist_id', core.customfields.BigIntegerField(null=True)),
                ('platform', models.CharField(max_length=256)),
                ('platform_type_id', models.ForeignKey(to='appinfo.PlatformType', db_column=b'platform_type_id', null=True, db_index=True)),
                ('category', models.CharField(max_length=256, null=True)),
                ('price', models.DecimalField(max_digits=30, decimal_places=10, null=True, default=0)),
                ('formatted_price', models.CharField(max_length=256, null=True)),
                ('currency', models.CharField(max_length=256, null=True)),
                ('description', models.TextField(null=True)),
                ('icon_url', models.CharField(max_length=4096, null=True)),
                ('rating', models.CharField(max_length=256, null=True)),
                ('rating1', core.customfields.BigIntegerField(null=True)),
                ('rating2', core.customfields.BigIntegerField(null=True)),
                ('rating3', core.customfields.BigIntegerField(null=True)),
                ('rating4', core.customfields.BigIntegerField(null=True)),
                ('rating5', core.customfields.BigIntegerField(null=True)),
                ('version', models.CharField(max_length=256, null=True)),
                ('content_rating', models.CharField(max_length=256, null=True)),
                ('size', models.CharField(max_length=256, null=True)),
                ('developer', models.CharField(max_length=256, null=True)),
                ('developer_email', models.CharField(max_length=256, null=True)),
                ('developer_website', models.CharField(max_length=256, null=True)),
                ('install', models.CharField(max_length=256, null=True)),
                ('has_iap',core.customfields.BigIntegerField(null=True)),
                ('iap_min', models.DecimalField(max_digits=30, decimal_places=10, null=True, default=0)),
                ('iap_max', models.DecimalField(max_digits=30, decimal_places=10, null=True, default=0)),
                ('release_date', models.DateTimeField(null=True)),
                ('fetch_time', models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                'db_table': 'app_info',
            },
            bases=(models.Model,),
        ),
        
        migrations.CreateModel(
            name='AppScreenshot',
            fields=[
                ('creation_time', models.DateTimeField(auto_now_add=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('app_screenshot_id', models.AutoField(serialize=False, primary_key=True)),
                ('screenshots', models.CharField(max_length=4096)),
                ('app_info_id', models.ForeignKey(to='appinfo.AppInfo', db_column=b'app_info_id')),
            ],
            options={
                'db_table': 'app_screenshots',
            },
            bases=(models.Model,),
        ),
        
        migrations.RunSQL(
            sql="""
                INSERT INTO platform_types
                    (creation_time, last_modified, platform_type_str, description)
                VALUES
                    (now(), now(), 'iOS', 'Apple''s iOS platform'),
                    (now(), now(), 'Android', 'The Android platform'),
                    (now(), now(), 'Web', 'Web platform')
                ;
            """,
        ),
    ]
