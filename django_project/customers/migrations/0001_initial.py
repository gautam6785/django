# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import core.customfields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Customer',
            fields=[
                ('creation_time', models.DateTimeField(auto_now_add=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('customer_id', models.AutoField(serialize=False, primary_key=True)),
                ('name', models.CharField(max_length=256,null=True)),
                ('timezone', models.CharField(default=b'America/Los_Angeles', max_length=256)),
                ('auth_user', models.ForeignKey(db_column=b'auth_user', to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'db_table': 'customers',
            },
            bases=(models.Model,),
        ),
        
        migrations.CreateModel(
            name='CustomerExternalLoginInfo',
            fields=[
                ('creation_time', models.DateTimeField(auto_now_add=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('login_info_id', models.AutoField(serialize=False, primary_key=True)),
                ('apple_vendor_id', models.BigIntegerField(null=True)),
                ('customer_id', models.ForeignKey(db_column=b'customer_id', to='customers.Customer', null=True)),
                ('external_service', models.CharField(db_index=True, max_length=256, choices=[(b'Google Cloud', b'Google Cloud'), (b'iTunes Connect', b'iTunes Connect')])),
                ('is_active', models.BooleanField(default=True)),
                ('password', core.customfields.EncryptedCharField(default='', max_length=256)),
                ('username', core.customfields.EncryptedCharField(default='', max_length=256)),
                ('apple_vendor_id', models.BigIntegerField(null=True, db_index=True)),
                ('gc_bucket_id', models.CharField(max_length=256, null=True)),
                ('refresh_token', core.customfields.EncryptedCharField(max_length=256, null=True)),
                ('refresh_token', core.customfields.EncryptedCharField(max_length=256, null=True)),
                ('step2_verification', models.BooleanField(default=True)),
            ],
            options={
                'db_table': 'customer_external_login_info',
            },
            bases=(models.Model,),
        ),
        
    ]
