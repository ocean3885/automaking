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
from django.contrib.auth.decorators import login_required

# Google Cloud TTS 관련 모듈
from google.cloud import texttospeech
from google.oauth2.service_account import Credentials
from django.core.exceptions import ImproperlyConfigured
from .utils import get_tts_client, get_voice_config, generate_tts_audio
from pydub import AudioSegment
import logging
logger = logging.getLogger(__name__)
from django.utils.text import slugify
from django.core.files.base import ContentFile
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from .models import AudioContent, Category

def home(request):
    """홈 페이지를 표시합니다."""
    return render(request, 'core/home.html')



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

@login_required
def upload_file_view(request):
    """파일 업로드 폼을 표시합니다."""
    # 템플릿은 중앙 templates 폴더에서 'core/upload_form.html'로 찾습니다.
    categories = Category.objects.all()
    return render(request, 'core/upload_form.html', {'categories': categories}) 

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
    
    # DB에 저장: 사용자가 로그인한 상태여야 함
    if request.user.is_authenticated:
        title = request.POST.get('title', 'Untitled')
        category_id = request.POST.get('category')
        category = None
        if category_id:
            try:
                category = Category.objects.get(id=int(category_id))
            except Category.DoesNotExist:
                category = None

        # 원문 및 번역(간단히 첫 쌍만 저장, 필요하면 전체 구조로 확장 가능)
        original_texts = '\n'.join([s['text'] for s in sentences_to_process])
        translated_texts = '\n'.join([s['translation'] for s in sentences_to_process])

        # create object without file first
        audio_obj = AudioContent.objects.create(
            user=request.user,
            title=title,
            category=category,
            original_text=original_texts,
            translated_text=translated_texts,
            audio_data=mp3_base64,
            sync_data=json.dumps(sync_data)
        )

        # save mp3 bytes to FileField
        filename = f"{slugify(title) or 'audio'}-{int(time.time())}.mp3"
        audio_obj.audio_file.save(filename, ContentFile(mp3_bytes))
        audio_obj.save()

        # 생성된 오디오의 상세 페이지로 리디렉트
        return redirect('audio_detail', audio_id=audio_obj.id)

    # 로그인하지 않은 경우 플레이어 페이지만 표시
    context = {
        'audio_data_uri': audio_data_uri,
        'sync_data_json': json.dumps(sync_data)  # JavaScript에서 사용할 수 있도록 JSON 문자열로 변환
    }
    return render(request, 'core/player.html', context)


@login_required
def audio_list(request):
    """사용자가 생성한 오디오 목록을 보여줍니다. 제목/카테고리로 필터링 가능."""
    qs = AudioContent.objects.filter(user=request.user)
    q = request.GET.get('q')
    category = request.GET.get('category')
    if q:
        qs = qs.filter(title__icontains=q)
    if category:
        qs = qs.filter(category_id=category)

    categories = Category.objects.all()
    context = {
        'audios': qs,
        'categories': categories,
        'search_query': q or '',
        'selected_category': int(category) if category else None,
    }
    return render(request, 'core/audio_list.html', context)


@login_required
def audio_detail(request, audio_id):
    audio = get_object_or_404(AudioContent, id=audio_id, user=request.user)
    
    # 조회수 증가
    audio.view_count += 1
    audio.save(update_fields=['view_count'])

    # original_text, translated_text를 줄 단위로 파싱하여 쌍으로 전달
    orig_lines = [ln.strip() for ln in (audio.original_text or '').splitlines() if ln.strip()]
    trans_lines = [ln.strip() for ln in (audio.translated_text or '').splitlines() if ln.strip()]
    sentences = []
    max_len = max(len(orig_lines), len(trans_lines))
    for i in range(max_len):
        o = orig_lines[i] if i < len(orig_lines) else ''
        t = trans_lines[i] if i < len(trans_lines) else ''
        sentences.append((o, t))

    # sync_data는 모델의 sync_data 필드에 JSON 문자열로 저장되어 있을 수 있음
    sync_data_list = []
    try:
        if audio.sync_data:
            sync_data_list = json.loads(audio.sync_data)
    except Exception:
        sync_data_list = []

    # sentences_with_times: 템플릿에서 사용할 문장 목록(원문, 번역, start, end)
    sentences_with_times = []
    if sync_data_list and len(sync_data_list) == len(sentences):
        for i, sd in enumerate(sync_data_list):
            o, t = sentences[i]
            sentences_with_times.append({
                'text': sd.get('text') or o,
                'translation': sd.get('translation') or t,
                'start': sd.get('start', 0),
                'end': sd.get('end', 0),
            })
    else:
        # sync 정보가 없거나 길이가 맞지 않으면 start/end를 0으로 채운 fallback 사용
        for o, t in sentences:
            sentences_with_times.append({'text': o, 'translation': t, 'start': 0, 'end': 0})

    context = {
        'audio': audio,
        'sentences': sentences,
        'sentences_with_times': sentences_with_times,
        'sync_data_json': json.dumps(sentences_with_times),
        'categories': Category.objects.all(),
    }
    return render(request, 'core/audio_detail.html', context)


@login_required
def add_category(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        name = data.get('name')
        if not name:
            return JsonResponse({'error': 'name required'}, status=400)

        category, created = Category.objects.get_or_create(name=name)
        return JsonResponse({'id': category.id, 'name': category.name})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def delete_audio(request, audio_id):
    audio = get_object_or_404(AudioContent, id=audio_id, user=request.user)
    if request.method == 'POST':
        audio.delete()
        return redirect('audio_list')
    return render(request, 'core/confirm_delete.html', {'audio': audio})


@login_required
def update_audio(request, audio_id):
    """오디오 제목과 카테고리를 업데이트합니다."""
    audio = get_object_or_404(AudioContent, id=audio_id, user=request.user)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    try:
        data = json.loads(request.body)
        
        # 제목 업데이트
        if 'title' in data:
            new_title = data['title'].strip()
            if new_title:
                audio.title = new_title
            else:
                return JsonResponse({'error': '제목은 비워둘 수 없습니다.'}, status=400)
        
        # 카테고리 업데이트
        if 'category_id' in data:
            try:
                category_id = int(data['category_id'])
                if category_id == 0:  # 카테고리 없음 선택
                    audio.category = None
                else:
                    category = get_object_or_404(Category, id=category_id)
                    audio.category = category
            except (ValueError, Category.DoesNotExist):
                return JsonResponse({'error': '잘못된 카테고리입니다.'}, status=400)
        
        audio.save()
        return JsonResponse({
            'success': True,
            'title': audio.title,
            'category': {
                'id': audio.category.id if audio.category else 0,
                'name': audio.category.name if audio.category else '카테고리 없음'
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': '잘못된 요청 형식입니다.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


