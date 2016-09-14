# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('metrics', '0001_initial'),
    ]

    operations = [
		migrations.AddField(
            model_name='GoogleReportRecord',
            name='timestamp',
            field=models.CharField(max_length=256, null=True),
        ),
      
        migrations.RunSQL(
			"ALTER TABLE `google_report_records` CHANGE `buyer_state` `buyer_state` VARCHAR( 256 ) CHARACTER SET utf8 COLLATE utf8_general_ci  NULL DEFAULT NULL"
		),
		
		migrations.RunSQL(
			"ALTER TABLE `google_report_records` CHANGE `buyer_city` `buyer_city` VARCHAR( 256 ) CHARACTER SET utf8 COLLATE utf8_general_ci  NULL DEFAULT NULL"
		)
    ]
