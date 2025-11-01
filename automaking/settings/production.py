"""
배포 환경 설정
"""
from .base import *
from django.core.exceptions import ImproperlyConfigured

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# 환경 변수에서 ALLOWED_HOSTS 로드
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')
if not ALLOWED_HOSTS or ALLOWED_HOSTS == ['']:
    raise ImproperlyConfigured("ALLOWED_HOSTS 환경 변수를 설정해주세요.")

# Database - Supabase PostgreSQL
# Supabase 프로젝트 설정에서 제공하는 연결 정보를 사용하세요
# Connection String 형식: postgresql://postgres:[PASSWORD]@[HOST]:[PORT]/postgres
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get('SUPABASE_DB_NAME', 'postgres'),
        "USER": os.environ.get('SUPABASE_DB_USER', 'postgres'),
        "PASSWORD": os.environ.get('SUPABASE_DB_PASSWORD'),
        "HOST": os.environ.get('SUPABASE_DB_HOST'),  # 예: db.xxxxxxxxxxxxx.supabase.co
        "PORT": os.environ.get('SUPABASE_DB_PORT', '5432'),
        'OPTIONS': {
            'sslmode': 'require',  # Supabase는 SSL 연결이 필요합니다
        },
        'CONN_MAX_AGE': 600,  # 연결 풀링 (10분)
    }
}

# Static files
STATIC_ROOT = os.environ.get('STATIC_ROOT', '/var/www/automaking/static/')
STATIC_URL = '/static/'

# Media files - Supabase Storage (S3 Compatible)
USE_S3_STORAGE = os.environ.get('USE_S3_STORAGE', 'False').lower() == 'true'

if USE_S3_STORAGE:
    # django-storages 설정
    if 'storages' not in INSTALLED_APPS:
        INSTALLED_APPS += ['storages']
    
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_S3_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_S3_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'ap-southeast-1')
    AWS_S3_ENDPOINT_URL = os.environ.get('AWS_S3_ENDPOINT_URL')
    
    # Supabase S3 presign requires SigV4
    AWS_S3_SIGNATURE_VERSION = 's3v4'
    AWS_S3_ADDRESSING_STYLE = 'path'
    
    # 프라이빗 버킷 설정
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',
    }
    AWS_DEFAULT_ACL = None  # 프라이빗 버킷은 ACL 사용 안 함
    AWS_QUERYSTRING_AUTH = True  # Signed URL 사용
    AWS_QUERYSTRING_EXPIRE = 3600  # Signed URL 유효 시간 (1시간)
    
    # HTTPS 연결 강제
    AWS_S3_USE_SSL = True
    AWS_S3_VERIFY = True  # SSL 인증서 검증
    
    # URL 관련 설정
    AWS_S3_CUSTOM_DOMAIN = None  # 커스텀 도메인 사용 안 함
    AWS_S3_URL_PROTOCOL = 'https:'  # HTTPS 사용
    
    # Supabase 프로젝트 URL (환경 변수에서 가져오기)
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_SERVICE_ROLE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
    
    # 환경별 폴더 prefix - 프로덕션은 'production/' 폴더에 저장
    STORAGE_ENVIRONMENT_PREFIX = 'production'
    
    # 커스텀 Storage 백엔드 사용
    DEFAULT_FILE_STORAGE = 'core.storage_backends.SupabasePrivateStorage'
    
    # MEDIA_URL은 동적으로 signed URL 생성
    MEDIA_URL = '/media/'  # 프록시 URL (뷰에서 signed URL로 리디렉트)
else:
    # 로컬 파일 시스템 사용 (개발/테스트용)
    MEDIA_ROOT = BASE_DIR / 'media'
    MEDIA_URL = '/media/'

# Security settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# HSTS 설정 (HTTPS 강제)
SECURE_HSTS_SECONDS = 31536000  # 1년
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# 로깅 설정
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'core': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
