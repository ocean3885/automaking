from django.urls import path
from . import views

urlpatterns = [
    # GET 요청: 파일을 업로드할 폼을 보여줌
    path('', views.upload_file_view, name='upload'), 
    # POST 요청: 파일 업로드를 받아 처리함
    path('process/', views.process_file_view, name='process'),
]