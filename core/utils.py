from google.cloud import texttospeech
# Django 설정 가져오기 (실제 Django 프로젝트에 맞게 수정)
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured 

def get_tts_client():
    """Google Cloud Text-to-Speech 클라이언트를 초기화합니다."""
    # 환경 변수나 Django 설정을 통해 인증 정보가 설정되어 있어야 합니다.
    # Google Application Default Credentials(ADC)를 사용하는 것이 일반적입니다.
    try:
        client = texttospeech.TextToSpeechClient()
        return client
    except Exception as e:
        raise ImproperlyConfigured(f"TTS 클라이언트 초기화 실패: {e}")

def get_voice_config(lang_code):
    """언어 코드에 따른 TTS 음성 설정을 반환합니다."""
    # 실제 사용 가능한 음성 이름으로 교체해야 합니다.
    if lang_code == 'es':
        # 예시: 스페인어 여성 목소리
        return texttospeech.VoiceSelectionParams(
            language_code="es-ES", 
            name="es-ES-Wavenet-D" # 실제 사용 가능한 Wavenet 음성
        )
    elif lang_code == 'ko':
        # 예시: 한국어 여성 목소리
        return texttospeech.VoiceSelectionParams(
            language_code="ko-KR", 
            name="ko-KR-Wavenet-A" # 실제 사용 가능한 Wavenet 음성
        )
    else:
        # 기본 음성
        return texttospeech.VoiceSelectionParams(language_code=lang_code)

def generate_tts_audio(client, text, voice_config, speaking_rate=1.0, volume_gain_db=0.0):
    """Google Cloud TTS API를 호출하여 오디오 콘텐츠(바이트)를 반환합니다."""
    synthesis_input = texttospeech.SynthesisInput(text=text)
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=speaking_rate, 
        volume_gain_db=volume_gain_db
    )
    
    response = client.synthesize_speech(
        input=synthesis_input, 
        voice=voice_config, 
        audio_config=audio_config
    )
    return response.audio_content