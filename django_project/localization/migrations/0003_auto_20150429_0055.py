# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('localization', '0002_country_display_name'),
    ]

    operations = [
      migrations.RunSQL(
                """
                UPDATE countries
                SET display_name = 'Bolivia'
                WHERE alpha2 = 'BO';

                UPDATE countries
                SET display_name = 'Cocos Islands'
                WHERE alpha2 = 'CC';

                UPDATE countries
                SET display_name = 'Congo'
                WHERE alpha2 = 'CD';

                UPDATE countries
                SET display_name = 'Falkland Islands'
                WHERE alpha2 = 'FK';

                UPDATE countries
                SET display_name = 'Holy See'
                WHERE alpha2 = 'VA';

                UPDATE countries
                SET display_name = 'Iran'
                WHERE alpha2 = 'IR';

                UPDATE countries
                SET display_name = 'North Korea'
                WHERE alpha2 = 'KP';

                UPDATE countries
                SET display_name = 'South Korea'
                WHERE alpha2 = 'KR';

                UPDATE countries
                SET display_name = 'Macedonia'
                WHERE alpha2 = 'MK';

                UPDATE countries
                SET display_name = 'Micronesia'
                WHERE alpha2 = 'FM';

                UPDATE countries
                SET display_name = 'Moldova'
                WHERE alpha2 = 'MD';

                UPDATE countries
                SET display_name = 'Palestine'
                WHERE alpha2 = 'PS';

                UPDATE countries
                SET display_name = 'Saint Helena'
                WHERE alpha2 = 'SH';

                UPDATE countries
                SET display_name = 'Saint Martin'
                WHERE alpha2 = 'MF';

                UPDATE countries
                SET display_name = 'Sint Maarten'
                WHERE alpha2 = 'SX';

                UPDATE countries
                SET display_name = 'Taiwan'
                WHERE alpha2 = 'TW';

                UPDATE countries
                SET display_name = 'Tanzania'
                WHERE alpha2 = 'TZ';

                UPDATE countries
                SET display_name = 'Venezuela'
                WHERE alpha2 = 'VE';

                UPDATE countries
                SET display_name = 'British Virgin Islands'
                WHERE alpha2 = 'VG';

                UPDATE countries
                SET display_name = 'U.S. Virgin Islands'
                WHERE alpha2 = 'VI';
                """,
        ),
    ]
