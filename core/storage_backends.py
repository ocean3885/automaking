import os
from io import BytesIO
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible
from supabase import create_client, Client

# --- Supabase 클라이언트 초기화 ---
# settings.py의 환경 변수를 읽어옵니다.
try:
    supabase_url = getattr(settings, 'SUPABASE_URL', '').rstrip('/')
    # 중요: Service Key를 사용해야 RLS를 우회하여 업로드/삭제가 가능합니다.
    service_key = getattr(settings, 'SUPABASE_SERVICE_KEY', None)
    
    if not supabase_url or not service_key:
        raise ValueError("SUPABASE_URL 또는 SUPABASE_SERVICE_KEY가 비어있습니다.")
        
    supabase: Client = create_client(supabase_url, service_key)

except (AttributeError, ValueError) as e:
    raise ImportError(
        f"SUPABASE_URL 및 SUPABASE_SERVICE_KEY가 settings.py에 올바르게 설정되어 있는지 확인하세요. 오류: {e}"
    )

@deconstructible
class SupabaseStorage(Storage):
    """
    Supabase Storage를 위한 Django 커스텀 스토리지 백엔드 (supabase-py SDK 사용)
    
    settings.py 필요 항목:
    - SUPABASE_URL
    - SUPABASE_SERVICE_ROLE_KEY
    - AWS_STORAGE_BUCKET_NAME (Supabase 버킷 이름)
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            # settings.py에서 버킷 이름을 가져옵니다.
            self.bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
            if not self.bucket_name:
                 raise ValueError("AWS_STORAGE_BUCKET_NAME이 비어있습니다.")
            self.environment_prefix = getattr(settings, 'STORAGE_ENVIRONMENT_PREFIX', 'local')
        except (AttributeError, ValueError) as e:
            raise ImportError(f"AWS_STORAGE_BUCKET_NAME이 settings.py에 올바르게 설정되어야 합니다. 오류: {e}")

    def _open(self, name, mode='rb'):
        """파일을 읽을 때 호출됩니다."""
        try:
            response = supabase.storage.from_(self.bucket_name).download(name)
            return ContentFile(response, name=name)
        except Exception as e:
            raise FileNotFoundError(f"Supabase '{name}' 파일 열기 실패: {e}")

    def _save(self, name, content):
        """
        파일을 저장할 때 호출됩니다.
        'name' (예: 'audios/file.mp3') 앞에 환경 prefix(예: 'production')를 붙입니다.
        """
        
        # 'name'이 이미 prefix로 시작하는지 확인 (마이그레이션 등)
        if not name.startswith(f"{self.environment_prefix}/"):
            # 'production' + '/' + 'audios/file.mp3' = 'production/audios/file.mp3'
            name = f"{self.environment_prefix}/{name}"
        
        try:
            supabase.storage.from_(self.bucket_name).upload(
                path=name,
                file=content.read(),
                file_options={"upsert": True}
            )
        except Exception as e:
            raise IOError(f"Supabase '{name}' 파일 저장 실패: {e}")
        
        # 'production/audios/file.mp3' (전체 경로)를 반환하여 DB에 저장
        return name

    def delete(self, name):
        """파일을 삭제할 때 호출됩니다."""
        try:
            supabase.storage.from_(self.bucket_name).remove([name])
        except Exception as e:
            print(f"[SupabaseStorage] 파일 '{name}' 삭제 중 오류 (무시): {e}")
            
    def exists(self, name):
        """파일 존재 여부를 확인합니다."""
        try:
            dir_path = os.path.dirname(name)
            file_name = os.path.basename(name)
            
            res = supabase.storage.from_(self.bucket_name).list(
                path=dir_path,
                options={"search": file_name, "limit": 1}
            )
            return any(item['name'] == file_name for item in res)
        except Exception:
            return False

    # --------------------------------------------------------------------------
    # [ 404 오류 / invalid path ] 해결을 위한 핵심 수정 지점
    # --------------------------------------------------------------------------
    def url(self, name):
        """
        파일에 접근할 수 있는 Presigned URL을 반환합니다.
        
        'name'은 버킷 내부의 실제 파일 경로입니다.
        (예: "production/audios/hablar-1761996515.mp3")
        """
        try:
            expires_in = 3600 # 1시간 유효
            res = supabase.storage.from_(self.bucket_name).create_signed_url(name, expires_in)
            
            if 'error' in res or 'data' not in res or 'signedUrl' not in res['data']:
                 raise ValueError(f"Supabase URL 서명 실패: {res.get('error')}")

            return res['data']['signedUrl']

        except Exception as e:
            print(f"[SupabaseStorage] URL 생성 중 오류: {e}")
            return ""