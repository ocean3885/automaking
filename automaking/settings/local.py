"""
로컬 개발 환경 설정
"""
from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Static files
STATIC_ROOT = BASE_DIR / 'staticfiles'


STORAGE_ENVIRONMENT_PREFIX = 'local'
    
    

