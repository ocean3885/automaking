from django.urls import path
from . import views

urlpatterns = [
    # 홈 페이지
    path('', views.home, name='home'),
    # 파일 업로드 폼
    path('upload/', views.upload_file_view, name='upload'),
    # 파일 처리
    path('process/', views.process_file_view, name='process'),
    # AI 문장 생성
    path('generate/', views.generate_sentences_view, name='generate_sentences'),
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
    
    # 보관함 관련
    path('collections/', views.collection_list, name='collection_list'),
    path('collections/<int:collection_id>/', views.collection_detail, name='collection_detail'),
    path('collections/create/', views.create_collection, name='create_collection'),
    path('collections/<int:collection_id>/delete/', views.delete_collection, name='delete_collection'),
    path('collections/<int:collection_id>/update/', views.update_collection, name='update_collection'),
    path('collections/list-json/', views.get_user_collections, name='get_user_collections'),
    path('audio/<int:audio_id>/add-to-collection/', views.add_to_collection, name='add_to_collection'),
    path('collections/<int:collection_id>/remove/<int:audio_id>/', views.remove_from_collection, name='remove_from_collection'),
]
