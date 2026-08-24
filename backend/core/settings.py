import os
from pathlib import Path
import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Initialize environment variables
env = environ.Env(
    DEBUG=(bool, True),
    DJANGO_SECRET_KEY=(str, 'django-insecure-default-dev-key-change-in-prod'),
    ALLOWED_HOSTS=(list, ['*']),
    DB_ENGINE=(str, 'sqlite'), # defaults to sqlite for quick local run or 'mysql'
    DB_NAME=(str, 'ticket_booking_db'),
    DB_USER=(str, 'ticket_user'),
    DB_PASSWORD=(str, 'ticket_password'),
    DB_HOST=(str, '127.0.0.1'),
    DB_PORT=(str, '3306'),
    REDIS_HOST=(str, '127.0.0.1'),
    REDIS_PORT=(int, 6379),
    CELERY_BROKER_URL=(str, 'redis://127.0.0.1:6379/0'),
    CELERY_RESULT_BACKEND=(str, 'redis://127.0.0.1:6379/0'),
    FRONTEND_URL=(str, 'http://localhost:5173'),
)

# Read .env if it exists
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env('DJANGO_SECRET_KEY')
DEBUG = env('DEBUG')

# Build ALLOWED_HOSTS: start with env-defined list, then auto-add Railway and Vercel domains
ALLOWED_HOSTS = env('ALLOWED_HOSTS')
# Automatically allow the Railway-assigned domain
_railway_host = os.environ.get('RAILWAY_PUBLIC_DOMAIN') or os.environ.get('RAILWAY_STATIC_URL')
if _railway_host and _railway_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_railway_host)
# Always allow all *.railway.app and *.vercel.app subdomains in production
ALLOWED_HOSTS += [
    '.railway.app',
    '.vercel.app',
    'web-production-6ecbf.up.railway.app',
    'ticket-sphere-sand.vercel.app',
]

# Application definition
INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'channels',

    # Local modular apps
    'accounts',
    'venues',
    'events',
    'bookings',
    'waitlist',
]

# Custom user model — must be set before first migration
AUTH_USER_MODEL = 'accounts.User'

ASGI_APPLICATION = 'core.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [
                (os.environ.get('REDIS_URL') or os.environ.get('REDISURL') or env('CELERY_BROKER_URL', default='redis://127.0.0.1:6379/0'), 
                 {'health_check_interval': 25, 'socket_keepalive': True})
            ],
        },
    },
}

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# Database Configuration — Railway injects DATABASE_URL automatically when PostgreSQL is linked.
# We parse it here and NEVER trust hand-typed DB_* variables to avoid the
# "invalid literal for int(): 'DB_PORT=3306'" class of errors.
DATABASE_URL_VAL = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')

if DATABASE_URL_VAL:
    import urllib.parse
    _url = urllib.parse.urlparse(DATABASE_URL_VAL)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': _url.path.lstrip('/'),
            'USER': _url.username,
            'PASSWORD': _url.password,
            'HOST': _url.hostname,
            'PORT': str(_url.port or 5432),
        }
    }
elif 'PGHOST' in os.environ or 'POSTGRES_HOST' in os.environ:
    # Fallback: individual PG vars injected by Railway / Heroku
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('PGDATABASE') or os.environ.get('POSTGRES_DB', 'railway'),
            'USER': os.environ.get('PGUSER') or os.environ.get('POSTGRES_USER', 'postgres'),
            'PASSWORD': os.environ.get('PGPASSWORD') or os.environ.get('POSTGRES_PASSWORD', ''),
            'HOST': os.environ.get('PGHOST') or os.environ.get('POSTGRES_HOST', 'localhost'),
            'PORT': os.environ.get('PGPORT') or os.environ.get('POSTGRES_PORT', '5432'),
        }
    }
else:
    # Local SQLite fallback (development only)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
            'OPTIONS': {'timeout': 20},
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
}

# SimpleJWT configuration
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'TOKEN_OBTAIN_SERIALIZER': 'accounts.views.CustomLoginSerializer',
}

# CORS configuration
from corsheaders.defaults import default_headers

FRONTEND_URL = env('FRONTEND_URL', default='https://ticket-sphere-sand.vercel.app')

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOWED_ORIGINS = [
    FRONTEND_URL,
    "https://ticket-sphere-sand.vercel.app",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

CSRF_TRUSTED_ORIGINS = [
    FRONTEND_URL,
    "https://ticket-sphere-sand.vercel.app",
    "https://web-production-6ecbf.up.railway.app",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
CORS_ALLOW_HEADERS = list(default_headers) + [
    'idempotency-key',
    'idempotencykey',
]

# Celery & Redis
REDIS_URL_VAL = os.environ.get('REDIS_URL') or os.environ.get('REDISURL') or env('CELERY_BROKER_URL')
CELERY_BROKER_URL = REDIS_URL_VAL
CELERY_RESULT_BACKEND = REDIS_URL_VAL
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TASK_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Seat Hold Configuration
HOLD_TTL_MINUTES = int(env('HOLD_TTL_MINUTES', default=10))

# Celery Beat Schedule
CELERY_BEAT_SCHEDULE = {
    'release-expired-holds-every-30-seconds': {
        'task': 'bookings.tasks.release_expired_holds',
        'schedule': 30.0,
    },
    'expire-waitlist-offers-every-30-seconds': {
        'task': 'waitlist.tasks.expire_waitlist_offers',
        'schedule': 30.0,
    },
}

# Email Configuration (Brevo 300 Free Emails/day or Console fallback)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')

default_email_backend = 'django.core.mail.backends.smtp.EmailBackend' if (EMAIL_HOST_USER and EMAIL_HOST_PASSWORD) else 'django.core.mail.backends.console.EmailBackend'

import sys
if 'test' in sys.argv:
    EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
else:
    EMAIL_BACKEND = env('EMAIL_BACKEND', default=default_email_backend)

EMAIL_HOST = env('EMAIL_HOST', default='smtp-relay.brevo.com')
EMAIL_PORT = int(env('EMAIL_PORT', default=587))
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='tickets@cinestream.in')
