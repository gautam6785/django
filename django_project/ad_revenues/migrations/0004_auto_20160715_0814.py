# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ad_revenues', '0003_auto_20160714_1617'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fid_data',
            name='fid',
            field=models.OneToOneField(related_name='fid_data', null=True, to='ad_revenues.credentials'),
        ),
    ]
