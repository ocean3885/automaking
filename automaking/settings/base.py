"""
Django base settings for automaking project.
모든 환경에서 공통으로 사용하는 설정입니다.
"""
from pathlib import Path
import os
from decouple import config, Csv
from django.core.exceptions import ImproperlyConfigured
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# -----------------------------------------------------------
# 환경 변수 로드 (.env 파일)
# -----------------------------------------------------------

# SECRET_KEY - 환경 변수에서 직접 로드 (배포 시 일관성 유지)
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    # 개발 환경에서는 decouple 사용 (로컬에서 .env 파일 사용)
    try:
        SECRET_KEY = config('SECRET_KEY')
    except Exception:
        raise ImproperlyConfigured("SECRET_KEY 환경 변수를 설정해주세요.")

# Google Cloud TTS 설정 (환경 변수에서 로드)
def get_google_cloud_credentials():
    """Google Cloud 서비스 계정 credentials를 환경 변수에서 가져오기"""
    try:
        # 환경 변수에서 직접 가져오기 시도 (배포 환경)
        project_id = os.environ.get('GOOGLE_CLOUD_PROJECT_ID')
        if not project_id:
            # 개발 환경에서는 decouple 사용
            project_id = config('GOOGLE_CLOUD_PROJECT_ID')
            
        private_key = os.environ.get('GOOGLE_CLOUD_PRIVATE_KEY')
        if not private_key:
            private_key = config('GOOGLE_CLOUD_PRIVATE_KEY')
            
        client_email = os.environ.get('GOOGLE_CLOUD_CLIENT_EMAIL')
        if not client_email:
            client_email = config('GOOGLE_CLOUD_CLIENT_EMAIL')
            
        credentials = {
            "type": "service_account",
            "project_id": project_id,
            "private_key_id": os.environ.get('GOOGLE_CLOUD_PRIVATE_KEY_ID') or config('GOOGLE_CLOUD_PRIVATE_KEY_ID'),
            "private_key": private_key.replace('\\n', '\n'),
            "client_email": client_email,
            "client_id": os.environ.get('GOOGLE_CLOUD_CLIENT_ID') or config('GOOGLE_CLOUD_CLIENT_ID'),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": os.environ.get('GOOGLE_CLOUD_CLIENT_CERT_URL') or config('GOOGLE_CLOUD_CLIENT_CERT_URL'),
            "universe_domain": "googleapis.com"
        }
        return credentials
    except Exception as e:
        raise ImproperlyConfigured(f"Google Cloud credentials 환경 변수가 올바르지 않습니다: {e}")

GOOGLE_CLOUD_CREDENTIALS_JSON = get_google_cloud_credentials()

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "core",
]

SITE_ID = 1

# -----------------------------------------------------------
# Storage (Supabase S3 compatible) - configure default storage
# -----------------------------------------------------------

# NOTE: Configure here so Django uses the correct default_storage for FileField.
USE_S3_STORAGE = config('USE_S3_STORAGE', default=False, cast=bool)

if USE_S3_STORAGE:
    if 'storages' not in INSTALLED_APPS:
        INSTALLED_APPS += ['storages']

    # S3-compatible (Supabase Storage) credentials
    AWS_ACCESS_KEY_ID = config('AWS_S3_ACCESS_KEY_ID', default=None)
    AWS_SECRET_ACCESS_KEY = config('AWS_S3_SECRET_ACCESS_KEY', default=None)
    AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME', default=None)
    AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='ap-southeast-1')
    AWS_S3_ENDPOINT_URL = config('AWS_S3_ENDPOINT_URL', default=None)
    # Force SigV4 for Supabase S3 compatibility (avoid legacy v2 presign which returns 403)
    AWS_S3_SIGNATURE_VERSION = 's3v4'
    # Ensure path-style addressing to match Supabase endpoint pattern
    AWS_S3_ADDRESSING_STYLE = 'path'

    # Supabase project info for signed URL generation
    SUPABASE_URL = config('SUPABASE_URL', default=None)
    SUPABASE_SERVICE_ROLE_KEY = config('SUPABASE_SERVICE_ROLE_KEY', default=None)

    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',
    }
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = True
    AWS_QUERYSTRING_EXPIRE = 3600

    # Default to local prefix; env-specific files can override (local/prod)
    STORAGE_ENVIRONMENT_PREFIX = os.environ.get('STORAGE_ENVIRONMENT_PREFIX', 'local')

    # Ensure custom storage is used globally
    DEFAULT_FILE_STORAGE = 'core.storage_backends.SupabasePrivateStorage'

# allauth 설정
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

LOGIN_REDIRECT_URL = '/'
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']
ACCOUNT_LOGIN_METHODS = {'email'}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "automaking.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        'DIRS': [BASE_DIR / 'templates'],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "automaking.wsgi.application"

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
LANGUAGE_CODE = 'ko-kr'
TIME_ZONE = 'Asia/Seoul'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"

# Media files (user uploaded)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
