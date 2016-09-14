# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('localization', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='country',
            name='display_name',
            field=models.CharField(max_length=256, null=True),
            preserve_default=True,
        ),
        migrations.RunSQL(
            sql="""
                UPDATE countries
                SET display_name = name;
                """,
        ),
    ]
