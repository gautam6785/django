"""
Scriber project Django settings common to all environments (development, testing, production).

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import djcelery
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

"""
TEMPLATE_DIRS = (
    BASE_DIR + '/templates/',
)

TEMPLATE_DEBUG = True
"""

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '9axuzpvdvj6jw*j6s^g=ida7kucqn%vx4dt(fzyotk_$^&#c#9'
ENCRYPTED_DB_FIELD_SECRET_KEY = os.environ.get("ENCRYPTED_DB_FIELD_SECRET_KEY", SECRET_KEY)

ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.humanize',
    'django.contrib.staticfiles',
    'django_forms_bootstrap',
    'djcelery',
    'kombu.transport.django',
    #'debug_toolbar',
    'customers',
    'appinfo',
    'dashboard',
    'download',
    'home',
    'localization',
    'metrics',
    'authentication',
    'utils',
    'base',
    'ad_revenues',
    #'mails', 
)

ROOT_URLCONF = 'mobbo.urls'

WSGI_APPLICATION = 'mobbo.wsgi.application'

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/
LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/
STATIC_URL = '/static/'
GOOGLE_PLAY_UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static/google_play/customers')
ITUNES_UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static/itunes/customers')

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, "static"),
)

# DEMO SETTINGS
DEFAULT_USER_ID = 1
DEMO_AUTH_USER_ID = 1



TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                # Insert your TEMPLATE_CONTEXT_PROCESSORS here or use this
                # list if you haven't customized them:
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.request',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

HOSTNAME=''
