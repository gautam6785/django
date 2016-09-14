# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('localization', '0004_auto_20150429_1647'),
    ]

    operations = [
    
    migrations.RunSQL(
            sql="""
            INSERT INTO countries
                    (`creation_time`, `last_modified`, `name`, `alpha2`, `alpha3`, `numeric`, `display_name`)
            VALUES
                    (now(), now(), 'Netherlands Antilles', 'AN', 'ANT', '599', 'Netherlands Antilles')
            ;
            """,
        ),
    
    ]
