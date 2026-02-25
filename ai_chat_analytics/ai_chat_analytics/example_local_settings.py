from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = ''

DEBUG = True

ALLOWED_HOSTS = ['*']

CORS_ALLOW_ALL_ORIGINS = True

# Database — SQLite for local dev
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    },
    'readonly': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    },
}

# For production use PostgreSQL:
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': '',
#         'USER': '',
#         'PASSWORD': '',
#         'HOST': 'localhost',
#         'PORT': '5432',
#     },
#     'readonly': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': '',
#         'USER': '',           # read-only DB user
#         'PASSWORD': '',
#         'HOST': 'localhost',
#         'PORT': '5432',
#         'OPTIONS': {'options': '-c default_transaction_read_only=on'}
#     },
# }

# Cache — local memory for dev, Redis for production
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'ai-chat-analytics',
    }
}

# For production use Redis:
# CACHES = {
#     'default': {
#         'BACKEND': 'django.core.cache.backends.redis.RedisCache',
#         'LOCATION': 'redis://127.0.0.1:6379/1',
#     }
# }

# OpenAI
OPENAI_API_KEY = ""

ENVIRONMENT = "Local"
