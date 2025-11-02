from django.db import models
from django.contrib.auth.models import User
from django.core.files.storage import default_storage
import os
import logging

# 로거 설정
logger = logging.getLogger(__name__)

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


def get_audio_storage():
    """동적으로 storage를 가져오기"""
    from django.conf import settings
    if settings.USE_S3_STORAGE:
        from core.storage import SupabaseStorage
        return SupabaseStorage()
    return default_storage

def audio_upload_path(instance, filename):
    """환경별 업로드 경로 설정"""
    from django.conf import settings
    prefix = getattr(settings, 'STORAGE_ENVIRONMENT_PREFIX', 'local')
    return f"{prefix}/audios/{filename}"

class AudioContent(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='audio_contents')
    title = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='audio_contents')
    original_text = models.TextField()
    translated_text = models.TextField()
    audio_file = models.FileField(upload_to=audio_upload_path, null=True, blank=True, storage=get_audio_storage)
    sync_data = models.TextField(null=True, blank=True)  # JSON 문자열 (타임스탬프)
    view_count = models.IntegerField(default=0)  # 조회수
    collections = models.ManyToManyField(Collection, related_name='audio_contents', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.user.username})"

    def delete(self, *args, **kwargs):
        """
        객체 삭제 시 연결된 파일도 함께 삭제합니다.
        (이 로직은 수정 없이 그대로 사용해도 좋습니다.)
        """
        if self.audio_file:
            try:
                # self.audio_file.storage.delete()와 동일하게 작동
                self.audio_file.delete(save=False)
            except Exception as e:
                logger.warning(f"오디오 파일 삭제 실패 (파일: {self.audio_file.name}): {e}")
        
        super().delete(*args, **kwargs)

    class Meta:
        ordering = ['-created_at']
