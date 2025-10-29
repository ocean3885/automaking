"""
Supabase Storage용 커스텀 Storage 백엔드
프라이빗 버킷에서 Signed URL을 생성합니다.
"""
from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings
import requests
import json
from datetime import datetime, timedelta


class SupabasePrivateStorage(S3Boto3Storage):
    """
    Supabase 프라이빗 버킷용 Storage 백엔드
    django-storages의 S3Boto3Storage를 상속받아 파일 업로드/삭제는 S3 호환 API 사용
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.querystring_auth = True
        self.default_acl = None
        
    def url(self, name, parameters=None, expire=None, http_method=None):
        """
        파일의 Signed URL을 생성합니다.
        Supabase Storage API를 사용하여 직접 signed URL 생성
        """
        if not name:
            return ''
        
        # Supabase REST API를 통한 signed URL 생성
        try:
            return self._generate_supabase_signed_url(name, expire or 3600)
        except Exception as e:
            # Fallback: boto3의 presigned URL 사용
            return super().url(name, parameters, expire, http_method)
    
    def _generate_supabase_signed_url(self, file_path, expires_in=3600):
        """
        Supabase Storage REST API로 signed URL 생성
        
        Args:
            file_path: 버킷 내 파일 경로 (예: 'audios/audio-123.mp3')
            expires_in: URL 유효 시간 (초)
        
        Returns:
            str: Signed URL
        """
        supabase_url = getattr(settings, 'SUPABASE_URL', None)
        service_role_key = getattr(settings, 'SUPABASE_SERVICE_ROLE_KEY', None)
        bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        
        if not supabase_url or not service_role_key:
            raise ValueError("SUPABASE_URL과 SUPABASE_SERVICE_ROLE_KEY가 필요합니다.")
        
        # Supabase Storage API 엔드포인트
        api_url = f"{supabase_url}/storage/v1/object/sign/{bucket_name}/{file_path}"
        
        headers = {
            'Authorization': f'Bearer {service_role_key}',
            'apikey': service_role_key,
            'Content-Type': 'application/json'
        }
        
        payload = {
            'expiresIn': expires_in
        }
        
        response = requests.post(api_url, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            signed_path = result.get('signedURL')
            if signed_path:
                # signedURL은 상대 경로로 반환됨 (/storage/v1/object/sign/...)
                return f"{supabase_url}{signed_path}"
        
        raise Exception(f"Signed URL 생성 실패: {response.status_code} - {response.text}")
