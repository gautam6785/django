# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ad_revenues', '0004_auto_20160715_0814'),
    ]

    operations = [
        migrations.RenameField(
            model_name='fid_data',
            old_name='fid',
            new_name='cred',
        ),
    ]
