# core/storage_backends.py
import json
import requests
from storages.backends.s3boto3 import S3Boto3Storage
from urllib.parse import quote

class SupabasePublicStorage(S3Boto3Storage):
    """
    Supabase Storage (public bucket)
    - 파일이 공개적으로 접근 가능한 버킷용
    """
    default_acl = 'public-read'
    file_overwrite = False


class SupabaseStorage(S3Boto3Storage):
    
    """
    Supabase Storage (private bucket)
    - 인증된 접근만 가능한 버킷
    - boto3를 통한 업로드/삭제는 그대로 두고, URL만 Supabase Signed URL로 대체
    """
    default_acl = 'private'
    file_overwrite = False

    def __init__(self, *args, **kwargs):
        from django.conf import settings        
        kwargs["bucket_name"] = settings.AWS_STORAGE_BUCKET_NAME
        super().__init__(*args, **kwargs)

    def url(self, name):
        from django.conf import settings
        """Supabase API로 signed URL 생성"""
        try:
            # 키 정규화 (선행 슬래시 제거 등)
            try:
                clean_name = self._clean_name(name)
                clean_name = self._normalize_name(clean_name) if hasattr(self, '_normalize_name') else clean_name
            except Exception:
                clean_name = name.lstrip('/')

            # 경로 인코딩 (슬래시는 보존)
            path = quote(clean_name.lstrip('/'), safe='/')

            supabase_url = settings.SUPABASE_URL.rstrip('/')
            service_role_key = settings.SUPABASE_SERVICE_KEY
            bucket = getattr(self, 'bucket_name', None) or settings.AWS_STORAGE_BUCKET_NAME
            expires_in = getattr(settings, 'AWS_QUERYSTRING_EXPIRE', 3600) or 3600

            # sign 요청
            endpoint = f"{supabase_url}/storage/v1/object/sign/{bucket}/{path}"
            payload = {"expiresIn": expires_in}
            headers = {
                "apikey": service_role_key,
                "Authorization": f"Bearer {service_role_key}",
                "Content-Type": "application/json",
            }
            response = requests.post(endpoint, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            data = response.json()
            signed_url = data.get("signedURL")
            if not signed_url:
                raise ValueError("signedURL 필드가 응답에 없습니다.")

            # 반환 URL 구성: /storage/v1 접두사 보장
            # 예: signed_url == "/object/sign/BUCKET/KEY?token=..."
            if signed_url.startswith("/storage/v1"):
                return f"{supabase_url}{signed_url}"
            return f"{supabase_url}/storage/v1{signed_url if signed_url.startswith('/') else '/' + signed_url}"

        except Exception as e:
            # 실패 시 boto3 presigned URL로 폴백
            print(f"[SupabaseStorage] signed URL 생성 실패 -> S3 presigned URL 폴백: {e}")
            return super().url(name)
