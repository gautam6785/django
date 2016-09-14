# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('localization', '0003_auto_20150429_0055'),
    ]

    operations = [
        migrations.AlterField(
            model_name='country',
            name='display_name',
            field=models.CharField(default='Invalid Country Display Name', max_length=256),
            preserve_default=False,
        ),
    ]
