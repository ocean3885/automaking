from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
import os

# User 모델 확장: 멤버십 정보 추가
class UserProfile(models.Model):
    """사용자 프로필 - 멤버십 정보"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    is_premium = models.BooleanField(default=False, verbose_name='프리미엄 멤버십')
    membership_started = models.DateTimeField(null=True, blank=True)
    membership_expires = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {'Premium' if self.is_premium else 'Free'}"

    @property
    def can_upload(self):
        """업로드 권한 확인 (프리미엄 멤버만)"""
        return self.is_premium

    class Meta:
        verbose_name = "사용자 프로필"
        verbose_name_plural = "사용자 프로필"


class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']


class Collection(models.Model):
    """사용자별 보관함"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='collections')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.name}"

    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'name']  # 같은 사용자는 같은 이름의 보관함을 중복 생성 불가


class AudioContent(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='audio_contents')
    title = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='audio_contents')
    original_text = models.TextField()
    translated_text = models.TextField()
    audio_data = models.TextField()  # Base64로 인코딩된 오디오 데이터
    # 환경에 따라 다른 스토리지 사용 (Supabase Storage or Local)
    # settings.USE_S3_STORAGE=True면 Supabase Storage를 사용하도록 강제
    try:
        from .storage_backends import SupabasePrivateStorage
    except Exception:
        SupabasePrivateStorage = None

    _storage_backend = SupabasePrivateStorage() if getattr(settings, 'USE_S3_STORAGE', False) and SupabasePrivateStorage else None

    audio_file = models.FileField(upload_to='audios/', storage=_storage_backend, null=True, blank=True)
    sync_data = models.TextField(null=True, blank=True)  # JSON 문자열으로 저장된 타임스탬프 데이터
    view_count = models.IntegerField(default=0)  # 조회수
    collections = models.ManyToManyField(Collection, related_name='audio_contents', blank=True)  # 보관함 다대다 관계
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.user.username})"

    def delete(self, *args, **kwargs):
        """
        오디오 파일 삭제 시 연결된 파일도 함께 삭제합니다.
        로컬 파일 시스템과 S3 호환 스토리지 모두 지원합니다.
        """
        if self.audio_file:
            try:
                # Django storage를 통해 삭제 (로컬/S3 모두 지원)
                self.audio_file.delete(save=False)
            except Exception as e:
                # 파일 삭제 실패 시 로깅 (선택사항)
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to delete audio file: {e}")
        super().delete(*args, **kwargs)

    class Meta:
        ordering = ['-created_at']
