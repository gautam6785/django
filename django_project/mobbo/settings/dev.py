"""
Scriber project Django settings for the production environment.
"""

from .common import *
from celery.schedules import crontab
from datetime import datetime, timedelta
from kombu import Exchange, Queue
from base64 import b64encode
from os import urandom

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

# LOGGING SETTINGS
BASE_LOG_DIR = '/var/www/Projects/mobbo-dashboards2/django_project/logs/'
ENCRYPTED_FIELD_KEYS_DIR = '/var/www/Projects/mobbo-dashboards2/django_project/keyset/'

#OAUTH2 key settings

# PKCS12 or PEM key provided by Google.
GOOGLE_KEY = '/var/www/Projects/mobbo-dashboards2/django_project/keyset/mobbo-dashboard-8cabe8c933e3.p12'
# JSON key provided by Google
JSON_KEY = '/var/www/Projects/mobbo-dashboards2/django_project/keyset/mobbo-dashboard-cc31d19cf175.json'

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.join(BASE_DIR, 'key/mobbo-dashboard-25d64dd9ef16.json')
#os.environ['GCLOUD_PROJECT'] = 'mobbo-dashboard'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format' : "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            'datefmt' : "%d/%b/%Y %H:%M:%S"
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': BASE_LOG_DIR + 'scriber_django.log',
            'formatter': 'verbose'
        },
        'console': {
            # logging handler that outputs log messages to terminal
            'class': 'logging.StreamHandler',
            'level': 'DEBUG', # message level to be written to console
        },
    },
    'loggers': {
        # root logger
        '': {
            'handlers': ['file'],
            'level': 'INFO',
        },
        'django': {
            'handlers': ['file'],
            'propagate': True,
            'level': 'INFO',
        },
        'ingestor': {
            'handlers': ['file'],
            'level': 'INFO',
        },
    }
}

# CELERY SETTINGS
# Since we use Redis as a cache backend, we connect to it over a socket file to avoid TCP overhead.
#BROKER_URL = 'redis+socket:///var/run/redis/redis.sock'

#djcelery.setup_loader()
#BROKER_URL = 'django://'
BROKER_URL = 'redis://localhost:6379'
CELERY_RESULT_BACKEND = 'redis://localhost:6379'
BROKER_TRANSPORT_OPTIONS = {'visibility_timeout': 18000}  # 5 hours
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_RESULT_BACKEND = 'redis+socket:///var/run/redis/redis.sock'
#CELERY_TIMEZONE = 'Europe/London'


CELERY_QUEUES = (
    Queue('default', Exchange('default', type='direct'), routing_key='default'),
)
CELERY_DEFAULT_QUEUE = 'default'
CELERY_DEFAULT_EXCHANGE = 'default'
CELERY_DEFAULT_ROUTING_KEY = 'default'
"""
class ScriberRouter(object):
    def route_for_task(self, task, *args, **kwargs):
        if task.startswith('realtime.') or task.startswith('ml.'):
            return {'queue': 'realtime'}
        elif task.startswith('appstore.tasks.fetch_missing_ios_artists'):
            return {'queue': 'default'}
        elif task.startswith('appstore.') or task.startswith('deeprank.'):
            return {'queue': 'rankings'}

CELERY_ROUTES = (ScriberRouter(), )
"""
#doneToken = b64encode(urandom(20)).rstrip('==')
# Note that crontab scheduling is in UTC time.

"""
CELERYBEAT_SCHEDULE = {
    'fetch_customer_google_apps': {
        'task': 'customers.tasks.fetch_customer_google_apps',
        'schedule': crontab(minute=38, hour=11),
        'args': (),
        'kwargs': {'login_info_id': 1},
    },
}
"""


"""
CELERYBEAT_SCHEDULE = {
    'daily-google-metrics-kickoff': {
        'task': 'metrics.tasks.reporttasks.daily_google_metrics_kickoff',
        'schedule': crontab(minute=18, hour=7),
        'args': (),
    },
}
"""

# Note that crontab scheduling is in UTC time.
CELERYBEAT_SCHEDULE = {
    'daily-apple-metrics-kickoff-americas': {
        'task': 'metrics.tasks.reporttasks.daily_apple_metrics_kickoff',
        'schedule': crontab(minute=58, hour=13),
        'args': (),
        'kwargs': {'timezone_str': 'America/Los_Angeles'},
    },
    'daily-google-metrics-kickoff': {
        'task': 'metrics.tasks.reporttasks.daily_google_metrics_kickoff',
        'schedule': crontab(minute=38, hour=13),
        'args': (),
        'kwargs': {'timezone_str': 'America/Los_Angeles'},
    },
    'hourly-sync-app-adRevenues-data': {
        'task'      : 'ad_revenues.tasks.DBsync.db_sync',
        'schedule'  : crontab(minute='*/2',hour="*"),
        'args'      : (),
        'kwargs'    : {},
    },
    #'daily-mails': {
        #'task'      : 'mails.tasks.daily_mails.mail_users',
        #'schedule'  : crontab(minute='*/2',hour="*"),
        #'args'      : (),
        #'kwargs'    : {},
    #}
}



# CACHE SETTINGS
CACHES = {
    'default': {
        'BACKEND': 'redis_cache.RedisCache',
        'LOCATION': '/var/run/redis/redis.sock',
        'OPTIONS': {
            'MAX_ENTRIES': 3000,
        },
    },
    'disk': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': '/var/tmp/appThetaCache',
        'TIMEOUT': 60 * 60 * 24 * 7,
        'OPTIONS': {
            'MAX_ENTRIES': 10000,
        },
    },
}

# DATABASE SETTINGS
PERSISTENT_DEFAULT_CONNECTION = 'persistent'
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'STORAGE_ENGINE': 'MYISAM',
        'NAME': 'mobbo-dashboards',
        'USER': 'root',
        'PASSWORD': 'ourdesignz',
        'HOST': 'localhost',
        'PORT': '',
        'OPTIONS': {
           "init_command": "SET storage_engine=MYISAM",
		} 
    },
    PERSISTENT_DEFAULT_CONNECTION: {
        'ENGINE': 'django.db.backends.mysql',
        'STORAGE_ENGINE': 'MYISAM',
        'NAME': 'mobbo-dashboards',
        'USER': 'root',
        'PASSWORD': 'ourdesignz',
        'HOST': 'localhost',
        'PORT': '',
        'CONN_MAX_AGE': 60*20,
        'OPTIONS': {
           "init_command": "SET storage_engine=MYISAM",
		} 
    },
}
DATABASE_ROUTERS = ['core.db.dynamic.DynamicDbRouter']

MIDDLEWARE_CLASSES = (
    'django.middleware.cache.UpdateCacheMiddleware',  # This must be first
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    #'django.middleware.cache.FetchFromCacheMiddleware',  # This must be last
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)

HOSTNAME = 'ggg.mobbo.com'
EMAIL_HOST = HOSTNAME