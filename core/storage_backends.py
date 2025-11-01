import requests
import logging
from urllib.parse import quote
from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage

logger = logging.getLogger(__name__)

class SupabasePrivateStorage(S3Boto3Storage):
    """Supabase 프라이빗 버킷용 Storage 백엔드"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.querystring_auth = True
        self.default_acl = None
        self.environment_prefix = getattr(settings, 'STORAGE_ENVIRONMENT_PREFIX', 'local')

    def get_available_name(self, name, max_length=None):
        if name.startswith(f'{self.environment_prefix}/'):
            return super().get_available_name(name, max_length)
        return super().get_available_name(f'{self.environment_prefix}/{name}', max_length)

    def _save(self, name, content):
        if not name.startswith(f'{self.environment_prefix}/'):
            name = f'{self.environment_prefix}/{name}'
        if hasattr(content, 'seek'):
            content.seek(0)
        return super()._save(name, content)

    def url(self, name, parameters=None, expire=None, http_method=None):
        if not name:
            return ''
        try:
            return self._generate_supabase_signed_url(name, expire or 3600)
        except Exception as e:
            logger.warning(f"Supabase signed URL 실패, fallback 사용: {e}")
            return super().url(name, parameters, expire, http_method)

    def _generate_supabase_signed_url(self, file_path, expires_in=3600):
        supabase_url = getattr(settings, 'SUPABASE_URL', '').rstrip('/')
        service_role_key = getattr(settings, 'SUPABASE_SERVICE_ROLE_KEY', None)
        bucket_name = settings.AWS_STORAGE_BUCKET_NAME

        if not supabase_url or not service_role_key:
            raise ValueError("SUPABASE_URL과 SUPABASE_SERVICE_ROLE_KEY가 필요합니다.")

        file_path = quote(file_path)
        api_url = f"{supabase_url}/storage/v1/object/sign/{bucket_name}/{file_path}"

        headers = {
            'Authorization': f'Bearer {service_role_key}',
            'apikey': service_role_key,
            'Content-Type': 'application/json'
        }

        payload = {'expiresIn': expires_in}

        response = requests.post(api_url, headers=headers, json=payload, timeout=10)

        if response.status_code == 200:
            result = response.json()
            if 'signedURL' in result:
                signed_path = result['signedURL']
                return f"{supabase_url}{signed_path}"

        logger.error(f"Signed URL 생성 실패: {response.status_code} - {response.text}")
        raise Exception(f"Signed URL 생성 실패: {response.status_code}")
