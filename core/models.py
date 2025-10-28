from django.db import models
from django.contrib.auth.models import User
import os

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
    audio_file = models.FileField(upload_to='audios/', null=True, blank=True)
    sync_data = models.TextField(null=True, blank=True)  # JSON 문자열으로 저장된 타임스탬프 데이터
    view_count = models.IntegerField(default=0)  # 조회수
    collections = models.ManyToManyField(Collection, related_name='audio_contents', blank=True)  # 보관함 다대다 관계
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.user.username})"

    def delete(self, *args, **kwargs):
        # 파일이 존재하면 물리적 파일도 삭제
        if self.audio_file:
            if os.path.isfile(self.audio_file.path):
                os.remove(self.audio_file.path)
        super().delete(*args, **kwargs)

    class Meta:
        ordering = ['-created_at']
