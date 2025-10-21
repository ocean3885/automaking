import io
import json
import os
import time
import base64
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, FileResponse
from django.urls import reverse
from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile

# Google Cloud TTS 관련 모듈
from google.cloud import texttospeech
from google.oauth2.service_account import Credentials
from django.core.exceptions import ImproperlyConfigured
from .utils import get_tts_client, get_voice_config, generate_tts_audio

os.environ["FFMPEG_PATH"] = "/usr/bin/ffmpeg" 
os.environ["FFPROBE_PATH"] = "/usr/bin/ffprobe"
# pydub를 사용하여 오디오 파일 처리 (FFmpeg 필요)
from pydub import AudioSegment

import logging
logger = logging.getLogger(__name__)

# -----------------------------------------------------------
# 1. TTS 클라이언트 초기화 함수 (settings.py의 Secret 사용)
# -----------------------------------------------------------

def get_tts_client():
    """settings.py에 정의된 JSON 자격 증명을 사용하여 TTS 클라이언트를 초기화합니다."""
    
    # 1. settings.py에서 인증 정보 로드
    credentials_json = settings.GOOGLE_CLOUD_CREDENTIALS_JSON
    
    if not credentials_json:
        raise ImproperlyConfigured("GOOGLE_CLOUD_CREDENTIALS_JSON이 settings.py에 정의되어 있지 않습니다.")
    
    # 2. JSON 데이터를 Credentials 객체로 변환
    credentials = Credentials.from_service_account_info(credentials_json)
    
    # 3. 클라이언트 생성 시 credentials 인수로 전달
    client = texttospeech.TextToSpeechClient(credentials=credentials)
    return client

# -----------------------------------------------------------
# 2. View 함수들
# -----------------------------------------------------------

# TTS 음성 및 파일 이름 규칙 정의 (임시 설정, 실제 서비스 언어에 따라 조정)
LANG_CONFIG = {
    'es': {'code': 'es-ES', 'voice': 'es-ES-Wavenet-B'},  # 스페인어 원문
    'ko': {'code': 'ko-KR', 'voice': 'ko-KR-Wavenet-D'}   # 한국어 번역
}

def upload_file_view(request):
    """파일 업로드 폼을 표시합니다."""
    # 템플릿은 중앙 templates 폴더에서 'core/upload_form.html'로 찾습니다.
    return render(request, 'core/upload_form.html') 

def process_file_view(request):
    """
    업로드된 TXT 파일을 처리하여,
    1. 원문 3회 반복 오디오를 생성하고,
    2. 각 문장의 재생 시간 정보(타임스탬프)를 계산한 뒤,
    3. 오디오 플레이어 페이지로 데이터를 전달하여 렌더링합니다.
    """
    if request.method != 'POST':
        return HttpResponseRedirect(reverse('upload'))

    # ... (기존의 파일 검증 및 파싱 코드는 그대로 사용) ...
    # 1. 파일 검증
    if 'input_file' not in request.FILES:
        return HttpResponse("파일을 첨부해주세요.", status=400)
    uploaded_file = request.FILES['input_file']
    if not uploaded_file.name.endswith('.txt'):
        return HttpResponse("TXT 파일만 업로드할 수 있습니다.", status=400)

    # 2. 파일 내용 읽기 및 파싱
    sentences_to_process = []
    try:
        file_content = uploaded_file.read().decode('utf-8')
        all_valid_lines = [
            line.strip() for line in file_content.split('\n') if line.strip()
        ]
        if len(all_valid_lines) % 2 != 0:
            print("WARNING: 파일의 유효한 줄 수가 홀수입니다. 마지막 줄이 버려집니다.")
        
        for i in range(0, len(all_valid_lines) - 1, 2):
            sentences_to_process.append({
                'text': all_valid_lines[i],
                'translation': all_valid_lines[i+1]
            })
    except Exception as e:
        return HttpResponse(f"파일 처리 중 오류 발생: {e}", status=500)

    # 3. TTS 클라이언트 생성 및 오디오 설정
    try:
        tts_client = get_tts_client()
        original_voice_config = get_voice_config('es')
    except Exception as e:
        return HttpResponse(f"API 클라이언트 초기화 오류: {e}", status=500)

    # 오디오 및 타임스탬프 데이터 준비
    combined_audio = AudioSegment.empty()
    sync_data = []  # 💡 [핵심 추가] 문장과 시간 정보를 저장할 리스트
    current_time_ms = 0.0  # 현재까지의 오디오 길이를 추적 (밀리초 단위)

    silent_break_between_sets = AudioSegment.silent(duration=2000)
    silent_break_for_repeat = AudioSegment.silent(duration=1000)

    # 4. 오디오 생성, 합치기 및 타임스탬프 계산
    for i, sentence_pair in enumerate(sentences_to_process):
        original_text = sentence_pair['text']
        try:
            audio_bytes = generate_tts_audio(tts_client, original_text, original_voice_config, speaking_rate=0.8, volume_gain_db=3.0)
            original_audio_clip = AudioSegment.from_file(io.BytesIO(audio_bytes), format="mp3")
            
            repeated_audio_clip = (
                silent_break_for_repeat + original_audio_clip +
                silent_break_for_repeat + original_audio_clip +
                silent_break_for_repeat + original_audio_clip +
                silent_break_for_repeat
            )

            # 💡 [핵심 추가] 타임스탬프 정보 계산 및 저장
            start_time = current_time_ms / 1000.0  # 초 단위로 변환
            duration = len(repeated_audio_clip) / 1000.0  # 초 단위로 변환
            end_time = start_time + duration
            
            sync_data.append({
                'text': sentence_pair['text'],
                'translation': sentence_pair['translation'],
                'start': start_time,
                'end': end_time
            })
            
            # 전체 오디오에 현재 클립 추가
            combined_audio += repeated_audio_clip
            current_time_ms += len(repeated_audio_clip)

            # 마지막 문장이 아니면 문장 세트 간의 공백 추가
            if i < len(sentences_to_process) - 1:
                combined_audio += silent_break_between_sets
                current_time_ms += len(silent_break_between_sets)

        except Exception as e:
            print(f"TTS 생성 중 오류 발생 for text: '{original_text[:20]}...'. Error: {e}")
            if i < len(sentences_to_process) - 1:
                combined_audio += silent_break_between_sets
                current_time_ms += len(silent_break_between_sets)

    # 5. 최종 오디오 데이터를 Base64로 인코딩하여 HTML에 삽입 준비
    if not combined_audio:
        return HttpResponse("생성된 오디오 클립이 없습니다.", status=500)
        
    combined_audio = combined_audio.normalize(headroom=-1.0)
    
    output_mp3_io = io.BytesIO()
    combined_audio.export(output_mp3_io, format="mp3")
    mp3_bytes = output_mp3_io.getvalue()
    
    # 💡 [핵심 추가] 오디오 데이터를 Base64로 인코딩하여 Data URI 생성
    mp3_base64 = base64.b64encode(mp3_bytes).decode('utf-8')
    audio_data_uri = f"data:audio/mpeg;base64,{mp3_base64}"
    
    # 💡 [핵심 추가] 템플릿에 데이터 전달 및 렌더링
    context = {
        'audio_data_uri': audio_data_uri,
        'sync_data_json': json.dumps(sync_data)  # JavaScript에서 사용할 수 있도록 JSON 문자열로 변환
    }
    
    return render(request, 'core/player.html', context)


