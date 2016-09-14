# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import core.oauth2client.django_orm


class Migration(migrations.Migration):

    dependencies = [
        ('ad_revenues', '0005_auto_20160715_0838'),
    ]

    operations = [
        migrations.CreateModel(
            name='adx_credentials',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('credential', core.oauth2client.django_orm.CredentialsField(null=True)),
            ],
        ),
    ]
