#!/usr/bin/env python3
import os
import sys
import io
import json
import time
import base64
import argparse
from datetime import datetime

# 1) Load env before Django setup

def load_env(env_path: str):
    if not env_path:
        return
    if not os.path.exists(env_path):
        print(f"[WARN] Env file not found: {env_path}")
        return
    print(f"[INFO] Loading env: {env_path}")
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            k, v = line.split('=', 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            # naive expansion for ${VAR}
            if '${' in v and '}' in v:
                for ref in [p for p in v.split('${') if '}' in p]:
                    ref_key = ref.split('}', 1)[0]
                    ref_val = os.environ.get(ref_key, '')
                    v = v.replace('${' + ref_key + '}', ref_val)
            os.environ.setdefault(k, v)


def init_django(settings_module: str):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)
    import django
    django.setup()


def which(program: str):
    """Simple which implementation."""
    for path in os.environ.get('PATH', '').split(os.pathsep):
        exe = os.path.join(path, program)
        if os.path.isfile(exe) and os.access(exe, os.X_OK):
            return exe
    return None


def get_ffmpeg_paths():
    # Try to find ffmpeg and ffprobe
    ffmpeg = which('ffmpeg') or '/usr/bin/ffmpeg'
    ffprobe = which('ffprobe') or '/usr/bin/ffprobe'
    return ffmpeg, ffprobe


def build_audio_segment(text: str, language: str, speed: float = 1.0, volume_change_db: float = 0.0):
    """Generate MP3 bytes using Google TTS via core.utils; fallback to 1-second silence on failure."""
    from pydub import AudioSegment
    try:
        from core.utils import get_tts_client, get_voice_config, generate_tts_audio
        tts_client = get_tts_client()
        voice = get_voice_config(language)
        mp3_bytes = generate_tts_audio(tts_client, text, voice, speed=speed)
        seg = AudioSegment.from_file(io.BytesIO(mp3_bytes), format='mp3')
        if abs(volume_change_db) > 0.001:
            seg = seg + volume_change_db
        return seg, mp3_bytes, None
    except Exception as e:
        # Fallback: 1 second of silence to validate storage path end-to-end
        print(f"[WARN] TTS failed, falling back to silence. Reason: {e}")
        from pydub import AudioSegment
        seg = AudioSegment.silent(duration=1000)
        out = io.BytesIO()
        ffmpeg, ffprobe = get_ffmpeg_paths()
        # Ensure pydub knows where ffmpeg is
        try:
            from pydub.utils import which as pydub_which
            from pydub import utils as pydub_utils
            AudioSegment.converter = ffmpeg
            AudioSegment.ffprobe = ffprobe
        except Exception:
            pass
        seg.export(out, format='mp3', bitrate='192k')
        return seg, out.getvalue(), e


def main():
    parser = argparse.ArgumentParser(description='AudioContent pipeline test: TTS -> pydub -> storage -> signed URL')
    parser.add_argument('--env', default='.env.production', help='Path to env file (default: .env.production)')
    parser.add_argument('--settings', default='automaking.settings.production', help='Django settings module')
    parser.add_argument('--username', default=None, help='Existing username to own the test content (default: first superuser or creates testuser)')
    parser.add_argument('--language', default='en-US', help='TTS language code (default: en-US)')
    parser.add_argument('--text', default='Hello world, this is a test.', help='Text to synthesize')
    parser.add_argument('--title', default=None, help='Title for AudioContent (default: auto with timestamp)')
    parser.add_argument('--repeat', type=int, default=1, help='Repeat count for the clip (default: 1)')
    parser.add_argument('--speed', type=float, default=1.0, help='Playback speed for TTS (default: 1.0)')
    parser.add_argument('--volume-db', type=float, default=0.0, help='Volume change in dB applied to clip (default: 0.0)')
    parser.add_argument('--keep', action='store_true', help='Keep the DB record and file (default: delete at the end)')
    parser.add_argument('--verify-download', action='store_true', help='Fetch the signed URL and verify bytes > 0')
    args = parser.parse_args()

    # Load env and init Django
    load_env(args.env)
    init_django(args.settings)

    from django.contrib.auth import get_user_model
    from django.core.files.base import ContentFile
    from django.utils.text import slugify
    from pydub import AudioSegment

    # Ensure pydub sees ffmpeg
    ffmpeg, ffprobe = get_ffmpeg_paths()
    AudioSegment.converter = ffmpeg
    AudioSegment.ffprobe = ffprobe
    print(f"[INFO] ffmpeg: {ffmpeg}, ffprobe: {ffprobe}")

    User = get_user_model()

    # Find or create user
    owner = None
    if args.username:
        owner = User.objects.filter(username=args.username).first()
        if not owner:
            print(f"[INFO] Username '{args.username}' not found, creating it (no password, is_staff=True)")
            owner = User.objects.create(username=args.username, is_staff=True)
    else:
        owner = User.objects.filter(is_superuser=True).first()
        if not owner:
            # Create a throwaway test user
            owner = User.objects.create(username='testuser', is_staff=True)
            print("[INFO] No superuser found; using 'testuser' as owner")

    # Build single clip via TTS (or silent fallback)
    seg, mp3_bytes, tts_error = build_audio_segment(args.text, args.language, args.speed, args.volume_db)

    # Repeat if requested
    combined = seg
    for _ in range(max(0, args.repeat - 1)):
        combined += seg

    # Export combined to mp3 bytes
    out = io.BytesIO()
    combined.export(out, format='mp3', bitrate='192k')
    final_bytes = out.getvalue()
    print(f"[INFO] Final MP3 size: {len(final_bytes)} bytes")

    # Prepare model fields
    now_str = datetime.utcnow().strftime('%Y%m%d-%H%M%S')
    title = args.title or f"Test Audio {now_str}"
    safe_title = slugify(title) or f"test-{now_str}"

    audio_data_b64 = base64.b64encode(final_bytes).decode('utf-8')
    sync_data = {
        'segments': [
            { 'text': args.text, 'start_ms': 0, 'end_ms': len(combined) }
        ],
        'repeat': args.repeat,
        'language': args.language,
        'note': 'generated by test1.py',
        'tts_error': str(tts_error) if tts_error else None,
    }

    # Create AudioContent and save file
    from core.models import AudioContent

    audio_obj = AudioContent(
        user=owner,
        title=title,
        original_text=args.text,
        translated_text=args.text,
        audio_data=audio_data_b64,
        sync_data=json.dumps(sync_data),
    )

    # Filename under the same prefix as templates expect (media/audios/)
    filename = f"audios/{safe_title}-{int(time.time())}.mp3"
    audio_obj.audio_file.save(filename, ContentFile(final_bytes), save=False)
    audio_obj.save()

    # Print details
    print("[RESULT] AudioContent created:")
    print(f"  id: {audio_obj.id}")
    print(f"  title: {audio_obj.title}")
    print(f"  file name: {audio_obj.audio_file.name}")
    try:
        url = audio_obj.audio_file.url
        print(f"  signed url: {url}")
    except Exception as e:
        url = None
        print(f"  [WARN] Could not get signed URL: {e}")

    # Verify download
    if args.verify_download and url:
        try:
            import requests
            r = requests.get(url, timeout=20)
            print(f"  GET status: {r.status_code}")
            print(f"  Content-Length: {len(r.content)}")
            ok = (r.status_code == 200 and len(r.content) > 0)
            print(f"  Download OK: {ok}")
        except Exception as e:
            print(f"  [ERROR] Download failed: {e}")

    # Cleanup if not keeping
    if not args.keep:
        # Delete will remove the file via storage delete
        try:
            obj_id = audio_obj.id
            audio_obj.delete()
            print(f"[CLEANUP] Deleted AudioContent id={obj_id} and its file")
        except Exception as e:
            print(f"[WARN] Cleanup failed: {e}")
    else:
        print("[INFO] Keeping the record and file as requested (--keep)")


if __name__ == '__main__':
    sys.exit(main())
