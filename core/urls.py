from django.urls import path
from . import views

urlpatterns = [
    # 홈 페이지
    path('', views.home, name='home'),
    # 파일 업로드 폼
    path('upload/', views.upload_file_view, name='upload'),
    # 파일 처리
    path('process/', views.process_file_view, name='process'),
    # 음성 파일 목록
    path('audios/', views.audio_list, name='audio_list'),
    # 카테고리 추가
    path('category/add/', views.add_category, name='add_category'),
    # 음성 파일 삭제
    path('audio/<int:audio_id>/delete/', views.delete_audio, name='delete_audio'),
    # 음성 파일 업데이트
    path('audio/<int:audio_id>/update/', views.update_audio, name='update_audio'),
    # 음성 파일 상세
    path('audio/<int:audio_id>/', views.audio_detail, name='audio_detail'),
]