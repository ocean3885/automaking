from django.db import models
from django.contrib.auth.models import User

class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

class AudioContent(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='audio_contents')
    title = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='audio_contents')
    original_text = models.TextField()
    translated_text = models.TextField()
    audio_data = models.TextField()  # Base64로 인코딩된 오디오 데이터
    audio_file = models.FileField(upload_to='audios/', null=True, blank=True)
    sync_data = models.TextField(null=True, blank=True)  # JSON 문자열으로 저장된 타임스탬프 데이터
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.user.username})"

    class Meta:
        ordering = ['-created_at']
