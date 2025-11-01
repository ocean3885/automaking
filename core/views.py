import io
import json
import os
import time
import base64
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, FileResponse
from django.urls import reverse
from django.conf import settings
from decouple import config
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.contrib.auth.decorators import login_required

# Google Cloud TTS 관련 모듈
from google.cloud import texttospeech
from google.oauth2.service_account import Credentials
from django.core.exceptions import ImproperlyConfigured
from .utils import get_tts_client, get_voice_config, generate_tts_audio
from pydub import AudioSegment
from pydub.utils import which
import logging
logger = logging.getLogger(__name__)
from django.utils.text import slugify
from django.core.files.base import ContentFile
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from .models import AudioContent, Category, Collection
from .decorators import premium_required, owner_or_premium_required

# Gemini AI 관련
import google.generativeai as genai

AudioSegment.converter = which("ffmpeg") or "/usr/bin/ffmpeg"
AudioSegment.ffprobe   = which("ffprobe") or "/usr/bin/ffprobe"

def home(request):
    """홈 페이지를 표시합니다. 카테고리별 최신 게시물을 보여줍니다."""
    # 게시물이 있는 카테고리만 가져오기
    categories_with_posts = Category.objects.filter(
        audio_contents__isnull=False
    ).distinct().order_by('name')
    
    # 각 카테고리별로 최신 게시물 5개씩 가져오기
    category_posts = []
    for category in categories_with_posts:
        posts = AudioContent.objects.filter(category=category).order_by('-created_at')[:5]
        if posts.exists():
            category_posts.append({
                'category': category,
                'posts': posts
            })
    
    # 카테고리 없는 게시물도 확인
    uncategorized_posts = AudioContent.objects.filter(category__isnull=True).order_by('-created_at')[:5]
    if uncategorized_posts.exists():
        category_posts.append({
            'category': None,
            'posts': uncategorized_posts
        })
    
    context = {
        'category_posts': category_posts,
        'total_posts': AudioContent.objects.count(),
        'total_categories': categories_with_posts.count()
    }
    
    return render(request, 'core/home.html', context)



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
@premium_required
def upload_file_view(request):
    """파일 업로드 폼을 표시합니다. (프리미엄 멤버 전용)"""
    # 템플릿은 중앙 templates 폴더에서 'core/upload_form.html'로 찾습니다.
    categories = Category.objects.all()
    return render(request, 'core/upload_form.html', {'categories': categories}) 

@login_required
@premium_required
def process_file_view(request):
    """
    업로드된 TXT 파일을 처리하여,
    1. 원문 3회 반복 오디오를 생성하고,
    2. 각 문장의 재생 시간 정보(타임스탬프)를 계산한 뒤,
    3. 오디오 플레이어 페이지로 데이터를 전달하여 렌더링합니다.
    (프리미엄 멤버 전용)
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
            sync_data=json.dumps(sync_data)
        )

        # save mp3 bytes to FileField
        filename = f"{slugify(title) or 'audio'}-{int(time.time())}.mp3"
        audio_obj.audio_file.save(filename, ContentFile(mp3_bytes))

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

    # 사용자의 모든 보관함에 포함된 오디오 ID 목록
    audio_ids_in_collections = set(
        Collection.objects.filter(user=request.user)
        .values_list('audio_contents__id', flat=True)
    )

    categories = Category.objects.all()
    context = {
        'audios': qs,
        'categories': categories,
        'search_query': q or '',
        'selected_category': int(category) if category else None,
        'audio_ids_in_collections': audio_ids_in_collections,
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

    # 이 오디오가 사용자의 보관함에 이미 추가되어 있는지 확인
    is_in_collection = Collection.objects.filter(
        user=request.user,
        audio_contents=audio
    ).exists()

    context = {
        'audio': audio,
        'sentences': sentences,
        'sentences_with_times': sentences_with_times,
        'sync_data_json': json.dumps(sentences_with_times),
        'categories': Category.objects.all(),
        'is_in_collection': is_in_collection,
    }
    return render(request, 'core/audio_detail.html', context)


@login_required
def add_category(request):
    # staff 권한 확인
    if not request.user.is_staff:
        return JsonResponse({'error': '카테고리 생성 권한이 없습니다.'}, status=403)
    
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
@owner_or_premium_required
def delete_audio(request, audio_id):
    """오디오 삭제 (본인 게시물만 가능)"""
    audio = get_object_or_404(AudioContent, id=audio_id, user=request.user)
    if request.method == 'POST':
        audio.delete()
        return redirect('audio_list')
    return render(request, 'core/confirm_delete.html', {'audio': audio})


@login_required
@owner_or_premium_required
def update_audio(request, audio_id):
    """오디오 제목과 카테고리를 업데이트합니다. (본인 게시물만 가능)"""
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


@login_required
@premium_required
def generate_sentences_view(request):
    """Gemini AI를 사용하여 학습용 문장을 생성합니다. (프리미엄 멤버 전용)"""
    if request.method != 'POST':
        return HttpResponseRedirect(reverse('upload'))
    
    # 파라미터 가져오기
    title = request.POST.get('title', 'AI 생성 문장')
    category_id = request.POST.get('category')
    source_language = request.POST.get('source_language')
    target_word = request.POST.get('target_word')
    sentence_count = int(request.POST.get('sentence_count', 5))
    
    # 언어 이름 매핑
    language_names = {
        'es': '스페인어',
        'en': '영어',
        'fr': '프랑스어',
        'de': '독일어',
        'ja': '일본어',
        'zh': '중국어'
    }
    
    try:
        # Gemini API 초기화
        gemini_api_key = config('GEMINI_API_KEY')
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # 프롬프트 생성
        lang_name = language_names.get(source_language, source_language)
        prompt = f"""당신은 외국어 학습 전문가입니다. 다음 조건에 맞는 문장을 생성해주세요:

        언어: {lang_name}
        학습할 단어/표현: {target_word}
        문장 개수: {sentence_count}개

        각 문장은 다음 형식으로 작성해주세요:
        1. {lang_name} 원문
        2. 한국어 번역

        요구사항:
        - '{target_word}'를 반드시 포함해야 합니다
        - 다양한 문맥에서 사용되는 예문
        - 스페인어의 경우 활용형(인칭,단수,복수,시제 등)을 다양하게 사용
        - 각 문장 쌍 사이에 빈 줄 추가

        **[필수 지침: 응답은 오직 요청된 문장 쌍만 포함해야 하며, 어떠한 설명, 서문, 제목도 포함해서는 안 됩니다. 첫 번째 줄은 반드시 {lang_name} 원문 문장으로 시작해야 합니다.]**

        출력 형식 (반드시 이 형식을 따라주세요):
        원문 문장
        한국어 번역
        ...
        """
        
        # AI 생성
        response = model.generate_content(prompt)
        generated_text = response.text.strip()

        # 생성된 텍스트를 파싱하여 문장 쌍으로 변환
        # 1. generated_text를 줄바꿈 기준으로 분리하고, 각 줄의 양 끝 공백과 빈 줄을 제거
        lines = [line.strip() for line in generated_text.split('\n') if line.strip()]

        # ------------------------------------------------------------
        # 2. [추가된 후처리 로직]: 첫 줄에 불필요한 서문이 있는지 확인하고 제거
        # ------------------------------------------------------------

        # 첫 줄이 있고, 해당 줄이 AI가 추가한 서문일 가능성이 높은지 확인 (예: 목록 시작, 설명 문구)
        # 스페인어 원문을 기대하므로, 한국어 설명 문구에 흔히 쓰이는 키워드가 포함되면 서문으로 간주합니다.
        if lines:
            first_line = lines[0].lower()
            # '다음은', '여기', '목록', '아래', '입니다' 등의 키워드가 포함되어 있으면 서문일 가능성이 높음
            if any(keyword in first_line for keyword in ['다음은', '여기', '목록', '아래', '입니다', '다음과']):
                # 첫 줄이 서문일 경우, 해당 줄을 제거합니다.
                lines = lines[1:]

        # ------------------------------------------------------------
        # 3. 파싱 로직 (기존 코드)
        # ------------------------------------------------------------
        sentences_to_process = []
        i = 0
        while i < len(lines):
            if i + 1 < len(lines):
                original = lines[i]
                translation = lines[i + 1]
                sentences_to_process.append({
                    'text': original,
                    'translation': translation
                })
                i += 2
            else:
                # 홀수 번째 줄만 남는 경우 (번역이 없는 경우), 해당 줄은 무시하고 종료
                i += 1
                
        if not sentences_to_process:
            # 후처리 후에도 문장 쌍이 없으면 에러 처리
            return HttpResponse("문장 생성에 실패했습니다. 다시 시도해주세요.", status=500)
        
        # TTS 처리 (기존 process_file_view와 동일한 로직)
        try:
            tts_client = get_tts_client()
            original_voice_config = get_voice_config(source_language)
        except Exception as e:
            return HttpResponse(f"TTS 클라이언트 초기화 오류: {e}", status=500)
        
        combined_audio = AudioSegment.empty()
        sync_data = []
        current_time_ms = 0.0
        
        silent_break_between_sets = AudioSegment.silent(duration=2000)
        silent_break_for_repeat = AudioSegment.silent(duration=1000)
        
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
                
                start_time = current_time_ms / 1000.0
                duration = len(repeated_audio_clip) / 1000.0
                end_time = start_time + duration
                
                sync_data.append({
                    'text': sentence_pair['text'],
                    'translation': sentence_pair['translation'],
                    'start': start_time,
                    'end': end_time
                })
                
                combined_audio += repeated_audio_clip
                current_time_ms += len(repeated_audio_clip)
                
                if i < len(sentences_to_process) - 1:
                    combined_audio += silent_break_between_sets
                    current_time_ms += len(silent_break_between_sets)
                    
            except Exception as e:
                logger.error(f"TTS 생성 중 오류: {e}")
                if i < len(sentences_to_process) - 1:
                    combined_audio += silent_break_between_sets
                    current_time_ms += len(silent_break_between_sets)
        
        if not combined_audio:
            return HttpResponse("생성된 오디오 클립이 없습니다.", status=500)
        
        combined_audio = combined_audio.normalize(headroom=-1.0)
        
        output_mp3_io = io.BytesIO()
        combined_audio.export(output_mp3_io, format="mp3")
        mp3_bytes = output_mp3_io.getvalue()
        
        mp3_base64 = base64.b64encode(mp3_bytes).decode('utf-8')
        
        # DB에 저장
        category = None
        if category_id:
            try:
                category = Category.objects.get(id=int(category_id))
            except Category.DoesNotExist:
                pass
        
        original_texts = '\n'.join([s['text'] for s in sentences_to_process])
        translated_texts = '\n'.join([s['translation'] for s in sentences_to_process])
        
        audio_obj = AudioContent.objects.create(
            user=request.user,
            title=title,
            category=category,
            original_text=original_texts,
            translated_text=translated_texts,
            sync_data=json.dumps(sync_data)
        )
        
        filename = f"{slugify(title) or 'ai-audio'}-{int(time.time())}.mp3"
        audio_obj.audio_file.save(filename, ContentFile(mp3_bytes))
        
        return redirect('audio_detail', audio_id=audio_obj.id)
        
    except Exception as e:
        logger.error(f"AI 문장 생성 오류: {e}")
        return HttpResponse(f"문장 생성 중 오류가 발생했습니다: {e}", status=500)


# -----------------------------------------------------------
# 보관함 관련 뷰
# -----------------------------------------------------------

@login_required
def collection_list(request):
    """사용자의 보관함 목록을 보여줍니다."""
    collections = Collection.objects.filter(user=request.user)
    return render(request, 'core/collection_list.html', {'collections': collections})


@login_required
def collection_detail(request, collection_id):
    """보관함의 상세 정보와 포함된 오디오를 보여줍니다."""
    collection = get_object_or_404(Collection, id=collection_id, user=request.user)
    audios = collection.audio_contents.all()
    return render(request, 'core/collection_detail.html', {
        'collection': collection,
        'audios': audios
    })


@login_required
def create_collection(request):
    """새 보관함을 생성합니다."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        
        if not name:
            return JsonResponse({'error': '보관함 이름을 입력해주세요.'}, status=400)

        # 같은 이름의 보관함이 있는지 확인
        if Collection.objects.filter(user=request.user, name=name).exists():
            return JsonResponse({'error': '같은 이름의 보관함이 이미 있습니다.'}, status=400)

        collection = Collection.objects.create(
            user=request.user,
            name=name,
            description=description
        )
        
        return JsonResponse({
            'id': collection.id,
            'name': collection.name,
            'description': collection.description
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def delete_collection(request, collection_id):
    """보관함을 삭제합니다."""
    collection = get_object_or_404(Collection, id=collection_id, user=request.user)
    
    if request.method == 'POST':
        collection.delete()
        return redirect('collection_list')
    
    return render(request, 'core/collection_confirm_delete.html', {'collection': collection})


@login_required
def update_collection(request, collection_id):
    """보관함 정보를 수정합니다."""
    collection = get_object_or_404(Collection, id=collection_id, user=request.user)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    try:
        data = json.loads(request.body)
        
        if 'name' in data:
            new_name = data['name'].strip()
            if not new_name:
                return JsonResponse({'error': '보관함 이름은 비워둘 수 없습니다.'}, status=400)
            
            # 같은 이름의 다른 보관함이 있는지 확인
            if Collection.objects.filter(user=request.user, name=new_name).exclude(id=collection_id).exists():
                return JsonResponse({'error': '같은 이름의 보관함이 이미 있습니다.'}, status=400)
            
            collection.name = new_name
        
        if 'description' in data:
            collection.description = data['description'].strip()
        
        collection.save()
        
        return JsonResponse({
            'success': True,
            'name': collection.name,
            'description': collection.description
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': '잘못된 요청 형식입니다.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def add_to_collection(request, audio_id):
    """오디오를 보관함에 추가합니다."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        # 오디오는 다른 사용자의 것도 추가 가능
        audio = get_object_or_404(AudioContent, id=audio_id)
        
        # 요청 본문 파싱
        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 오류: {e}")
            return JsonResponse({'error': 'JSON 형식이 잘못되었습니다.'}, status=400)
        
        collection_id = data.get('collection_id')
        
        if not collection_id:
            return JsonResponse({'error': '보관함을 선택해주세요.'}, status=400)

        # 보관함은 본인 것만
        try:
            collection = Collection.objects.get(id=collection_id, user=request.user)
        except Collection.DoesNotExist:
            return JsonResponse({'error': '보관함을 찾을 수 없습니다.'}, status=404)
        
        # 이미 추가되어 있는지 확인
        if collection.audio_contents.filter(id=audio_id).exists():
            return JsonResponse({'error': '이미 이 보관함에 추가되어 있습니다.'}, status=400)
        
        collection.audio_contents.add(audio)
        
        logger.info(f"Audio {audio_id} added to collection {collection_id} by user {request.user.username}")
        
        return JsonResponse({
            'success': True,
            'message': f'"{audio.title}"을(를) "{collection.name}" 보관함에 추가했습니다.'
        })
    except Exception as e:
        logger.error(f"보관함 추가 오류: {e}", exc_info=True)
        return JsonResponse({'error': f'오류가 발생했습니다: {str(e)}'}, status=500)


@login_required
def remove_from_collection(request, collection_id, audio_id):
    """보관함에서 오디오를 제거합니다."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        collection = get_object_or_404(Collection, id=collection_id, user=request.user)
        audio = get_object_or_404(AudioContent, id=audio_id)
        
        collection.audio_contents.remove(audio)
        
        return JsonResponse({
            'success': True,
            'message': '보관함에서 제거되었습니다.'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_user_collections(request):
    """사용자의 보관함 목록을 JSON으로 반환합니다."""
    collections = Collection.objects.filter(user=request.user)
    data = [
        {
            'id': c.id,
            'name': c.name,
            'count': c.audio_contents.count()
        }
        for c in collections
    ]
    return JsonResponse({'collections': data})

