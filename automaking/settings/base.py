"""
Django base settings for automaking project.
모든 환경에서 공통으로 사용하는 설정입니다.
"""
from pathlib import Path
import os
from decouple import config, Csv
from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# -----------------------------------------------------------
# 환경 변수 로드 (.env 파일)
# -----------------------------------------------------------

# SECRET_KEY
SECRET_KEY = config('SECRET_KEY')

# Google Cloud TTS 설정 (환경 변수에서 로드)
def get_google_cloud_credentials():
    """Google Cloud 서비스 계정 credentials를 환경 변수에서 가져오기"""
    try:
        credentials = {
            "type": "service_account",
            "project_id": config('GOOGLE_CLOUD_PROJECT_ID'),
            "private_key_id": config('GOOGLE_CLOUD_PRIVATE_KEY_ID'),
            "private_key": config('GOOGLE_CLOUD_PRIVATE_KEY').replace('\\n', '\n'),
            "client_email": config('GOOGLE_CLOUD_CLIENT_EMAIL'),
            "client_id": config('GOOGLE_CLOUD_CLIENT_ID'),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": config('GOOGLE_CLOUD_CLIENT_CERT_URL'),
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
