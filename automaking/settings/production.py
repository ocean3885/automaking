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

    
# HTTPS 연결 강제
AWS_S3_USE_SSL = True
AWS_S3_VERIFY = True  # SSL 인증서 검증

# URL 관련 설정
AWS_S3_CUSTOM_DOMAIN = None  # 커스텀 도메인 사용 안 함
AWS_S3_URL_PROTOCOL = 'https:'  # HTTPS 사용

# 환경별 폴더 prefix - 프로덕션은 'production/' 폴더에 저장
STORAGE_ENVIRONMENT_PREFIX = 'production'

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
