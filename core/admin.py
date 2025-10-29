from django.contrib import admin
from .models import Category, AudioContent, Collection, UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_premium', 'membership_started', 'membership_expires', 'created_at']
    list_filter = ['is_premium', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('사용자 정보', {
            'fields': ('user',)
        }),
        ('멤버십 정보', {
            'fields': ('is_premium', 'membership_started', 'membership_expires')
        }),
        ('타임스탬프', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']

@admin.register(AudioContent)
class AudioContentAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'category', 'view_count', 'created_at']
    list_filter = ['category', 'created_at']
    search_fields = ['title', 'user__username']
    readonly_fields = ['view_count', 'created_at', 'updated_at']

@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'audio_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'user__username', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    def audio_count(self, obj):
        return obj.audio_contents.count()
    audio_count.short_description = '오디오 수'
