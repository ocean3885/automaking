"""
로컬 개발 환경 설정
"""
from .base import *
from decouple import config

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

# Media files - Supabase Storage (로컬 개발 환경에서도 사용)
USE_S3_STORAGE = config('USE_S3_STORAGE', default='False', cast=bool)

if USE_S3_STORAGE:
    # django-storages 설정
    if 'storages' not in INSTALLED_APPS:
        INSTALLED_APPS += ['storages']
    
    AWS_ACCESS_KEY_ID = config('AWS_S3_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = config('AWS_S3_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='ap-southeast-1')
    AWS_S3_ENDPOINT_URL = config('AWS_S3_ENDPOINT_URL')
    # Supabase S3 presign requires SigV4
    AWS_S3_SIGNATURE_VERSION = 's3v4'
    AWS_S3_ADDRESSING_STYLE = 'path'
    
    # 프라이빗 버킷 설정
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',
    }
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = True
    AWS_QUERYSTRING_EXPIRE = 3600
    
    # Supabase 설정
    SUPABASE_URL = config('SUPABASE_URL')
    SUPABASE_SERVICE_ROLE_KEY = config('SUPABASE_SERVICE_ROLE_KEY')
    
    # 환경별 폴더 prefix - 로컬은 'local/' 폴더에 저장
    STORAGE_ENVIRONMENT_PREFIX = 'local'
    
    # 커스텀 Storage 백엔드 사용
    DEFAULT_FILE_STORAGE = 'core.storage_backends.SupabasePrivateStorage'
    
    MEDIA_URL = '/media/'
else:
    # 로컬 파일 시스템 사용 (기본값)
    MEDIA_ROOT = BASE_DIR / 'media'
    MEDIA_URL = '/media/'

