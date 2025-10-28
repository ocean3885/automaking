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

# 개발 환경용 추가 설정
# 디버그 툴바 등 필요한 경우 여기에 추가
