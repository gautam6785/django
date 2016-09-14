from __future__ import absolute_import

import os
from celery import Celery
from django.conf import settings

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mobbo.settings.prod')
#os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mobbo.settings.dev')

app = Celery(include=[
    'metrics.tasks.reporttasks',
    'ad_revenues.tasks.DBsync',
    #'mails.tasks.daily_mails',
    #'metrics.tasks.tasks',
])

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object(os.environ['DJANGO_SETTINGS_MODULE'])
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
