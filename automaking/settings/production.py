"""
배포 환경 설정
"""
from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# 실제 도메인으로 변경하세요
ALLOWED_HOSTS = ['your-domain.com', 'www.your-domain.com']

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
STATIC_ROOT = '/var/www/automaking/static/'
STATIC_URL = '/static/'

# Media files (Supabase Storage 사용 권장)
# 추후 django-storages와 supabase-py를 사용하여 Supabase Storage로 변경 가능
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

# CORS 설정 (필요한 경우)
# CORS_ALLOWED_ORIGINS = [
#     "https://your-domain.com",
# ]

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
