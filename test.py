import os
import sys
import time
import uuid
import json
import argparse
import traceback

def mask(val: str, keep=4):
    if not val:
        return ""
    if len(val) <= keep * 2:
        return "*" * len(val)
    return val[:keep] + "*" * (len(val) - keep * 2) + val[-keep:]

def load_env(env_path):
    env = {}
    if os.path.isfile(env_path):
        try:
            # python-dotenv 없이 간단 파서
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    env[k] = v
        except Exception:
            print("[WARN] .env 파일 파싱 중 오류, 무시하고 진행합니다.")
    return env

def guess_endpoint(env):
    endpoint = env.get("AWS_S3_ENDPOINT_URL") or os.environ.get("AWS_S3_ENDPOINT_URL")
    if endpoint:
        return endpoint
    # SUPABASE_URL이 있으면 /storage/v1/s3 로 유추
    url = env.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL")
    if url:
        if url.endswith("/"):
            url = url[:-1]
        return f"{url}/storage/v1/s3"
    # project-ref 기반으로도 유추 가능 (jsyqcaozqtgsfoicerpo.supabase.co)
    host = env.get("SUPABASE_HOST") or os.environ.get("SUPABASE_HOST")
    if host:
        return f"https://{host}/storage/v1/s3"
    return None

def resolve_config(env):
    cfg = {}
    cfg["AWS_ACCESS_KEY_ID"] = os.environ.get("AWS_S3_ACCESS_KEY_ID") or env.get("AWS_S3_ACCESS_KEY_ID")
    cfg["AWS_SECRET_ACCESS_KEY"] = os.environ.get("AWS_S3_SECRET_ACCESS_KEY") or env.get("AWS_S3_SECRET_ACCESS_KEY")
    cfg["AWS_S3_ENDPOINT_URL"] = guess_endpoint(env)
    cfg["AWS_S3_REGION_NAME"] = os.environ.get("AWS_S3_REGION_NAME") or env.get("AWS_S3_REGION_NAME") or "us-east-1"
    cfg["BUCKET"] = (
        os.environ.get("SUPABASE_STORAGE_BUCKET")
        or env.get("SUPABASE_STORAGE_BUCKET")
        or os.environ.get("AWS_STORAGE_BUCKET_NAME")
        or env.get("AWS_STORAGE_BUCKET_NAME")
        or "media"
    )
    return cfg

def print_config(cfg):
    print("=== Supabase S3 설정 점검 ===")
    print(f"Bucket                : {cfg['BUCKET']}")
    print(f"Endpoint URL          : {cfg['AWS_S3_ENDPOINT_URL']}")
    print(f"AWS_ACCESS_KEY_ID     : {mask(cfg['AWS_ACCESS_KEY_ID'])}")
    print(f"AWS_SECRET_ACCESS_KEY : {mask(cfg['AWS_SECRET_ACCESS_KEY'])}")
    print(f"Region                : {cfg['AWS_S3_REGION_NAME']}")
    print("============================")

def ensure_requirements():
    missing = []
    try:
        import boto3  # noqa
        from botocore.client import Config  # noqa
    except Exception:
        missing.append("boto3")
    try:
        import requests  # noqa
    except Exception:
        missing.append("requests")
    if missing:
        print(f"[ERROR] 필요한 패키지가 없습니다: {', '.join(missing)}")
        print("       가상환경에서 다음 명령으로 설치하세요:")
        print("       pip install " + " ".join(missing))
        sys.exit(1)

def s3_client(cfg):
    import boto3
    from botocore.client import Config
    session = boto3.session.Session(
        aws_access_key_id=cfg["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=cfg["AWS_SECRET_ACCESS_KEY"],
        region_name=cfg["AWS_S3_REGION_NAME"],
    )
    return session.client(
        "s3",
        endpoint_url=cfg["AWS_S3_ENDPOINT_URL"],
        config=Config(signature_version="s3v4"),
        verify=True,
    )

def test_upload_download(cfg, keep=False, prefix="health"):
    import requests
    s3 = s3_client(cfg)

    # 1) 버킷 접근 확인
    print("[1/4] 버킷 접근 확인 (HeadBucket)...")
    try:
        s3.head_bucket(Bucket=cfg["BUCKET"])
        print("     ✅ 버킷 접근 성공")
    except Exception as e:
        print("     ❌ 버킷 접근 실패")
        raise

    # 2) 업로드
    key = f"{prefix}/{int(time.time())}-{uuid.uuid4().hex}.txt"
    body = f"ping from test.py at {time.strftime('%Y-%m-%d %H:%M:%S')}\n".encode("utf-8")
    print(f"[2/4] 업로드 실행: s3://{cfg['BUCKET']}/{key}")
    try:
        s3.put_object(
            Bucket=cfg["BUCKET"],
            Key=key,
            Body=body,
            ContentType="text/plain",
        )
        print("     ✅ 업로드 성공")
    except Exception as e:
        print("     ❌ 업로드 실패")
        raise

    # 3) 객체 확인 + presigned URL 생성
    print("[3/4] 객체 확인 및 서명 URL 생성...")
    try:
        head = s3.head_object(Bucket=cfg["BUCKET"], Key=key)
        size = head.get("ContentLength")
        print(f"     ✅ 객체 확인 성공 (size={size})")
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": cfg["BUCKET"], "Key": key},
            ExpiresIn=300,
        )
        print("     Presigned URL:", url)
    except Exception as e:
        print("     ❌ presigned URL 생성 실패")
        raise

    # 4) presigned URL로 실제 다운로드 확인
    print("[4/4] presigned URL 다운로드 검증...")
    try:
        r = requests.get(url, timeout=15)
        ok = (r.status_code == 200) and (r.content == body)
        print(f"     상태코드={r.status_code}, 길이={len(r.content)}")
        if ok:
            print("     ✅ 다운로드 검증 성공 (내용 일치)")
        else:
            print("     ❌ 다운로드 검증 실패 (내용 불일치)")
            print("        응답 미리보기:", r.content[:200])
            raise RuntimeError("Downloaded content mismatch")
    except Exception:
        raise

    if not keep:
        try:
            s3.delete_object(Bucket=cfg["BUCKET"], Key=key)
            print(f"     🧹 테스트 파일 삭제 완료: {key}")
        except Exception:
            print("     ⚠️ 테스트 파일 삭제 실패(무시)")

def try_django_storage(prefix="health"):
    print("\n=== Django default_storage 점검(옵션) ===")
    try:
        import django
        from django.conf import settings as dj_settings
        from django.core.files.base import ContentFile
        from django.core.files.storage import default_storage
    except Exception:
        print("Django 모듈을 불러올 수 없어 건너뜁니다.")
        return

    # 프로젝트 루트 추정
    root = os.path.dirname(os.path.abspath(__file__))
    if root not in sys.path:
        sys.path.insert(0, root)

    # 환경 변수 로드 시도
    env_path = os.path.join(root, ".env.production")
    env = load_env(env_path)
    for k, v in env.items():
        os.environ.setdefault(k, v)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "automaking.settings.production")

    try:
        django.setup()
    except Exception as e:
        print("Django 설정 초기화 실패, 건너뜁니다.")
        print(e)
        return

    try:
        name = f"{prefix}/{int(time.time())}-{uuid.uuid4().hex}.txt"
        content = ContentFile(b"ping from django default_storage\n")
        saved = default_storage.save(name, content)
        url = default_storage.url(saved)
        print(f"default_storage.save OK: {saved}")
        print(f"default_storage.url     : {url}")

        import requests
        r = requests.get(url, timeout=15)
        print(f"GET {r.status_code}, len={len(r.content)}")
        if r.status_code == 200:
            print("✅ Django storage로도 업로드/접근 성공")
        else:
            print("❌ Django storage 접근 실패")
    except Exception as e:
        print("❌ Django storage 테스트 실패")
        traceback.print_exc()

def main():
    parser = argparse.ArgumentParser(description="Supabase Storage 업로드/다운로드 헬스체크")
    parser.add_argument("--env", default=".env.production", help="환경변수 파일 경로 (.env.production)")
    parser.add_argument("--keep", action="store_true", help="테스트 업로드 파일을 삭제하지 않음")
    parser.add_argument("--prefix", default="health", help="업로드 키 접두사(prefix)")
    parser.add_argument("--skip-django", action="store_true", help="Django default_storage 테스트 생략")
    args = parser.parse_args()

    ensure_requirements()

    env_path = os.path.abspath(args.env)
    env = load_env(env_path)
    cfg = resolve_config(env)

    # 기본 유효성 검사
    errors = []
    if not cfg["AWS_ACCESS_KEY_ID"]:
        errors.append("AWS_ACCESS_KEY_ID 없음 (Supabase Storage > S3 credentials 사용)")
    if not cfg["AWS_SECRET_ACCESS_KEY"]:
        errors.append("AWS_SECRET_ACCESS_KEY 없음 (Supabase Storage > S3 credentials 사용)")
    if not cfg["AWS_S3_ENDPOINT_URL"]:
        errors.append("AWS_S3_ENDPOINT_URL 없음 (예: https://<project-ref>.supabase.co/storage/v1/s3)")
    if not cfg["BUCKET"]:
        errors.append("버킷 이름이 비어있음")

    print_config(cfg)

    if errors:
        print("환경 변수 오류:")
        for e in errors:
            print(" -", e)
        # 흔한 착오 경고
        if (env.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")) and not cfg["AWS_ACCESS_KEY_ID"]:
            print("⚠️ 주의: service_role 키는 S3 업로드에 사용할 수 없습니다. Supabase Storage > Settings > S3 credentials의 Access/Secret Key를 사용하세요.")
        sys.exit(1)

    try:
        test_upload_download(cfg, keep=args.keep, prefix=args.prefix)
        print("\n✅ S3 호환 경로 업로드/다운로드 테스트 성공")
    except Exception:
        print("\n❌ S3 테스트 실패. 상세 오류:")
        traceback.print_exc()
        print("\n체크리스트:")
        print(" 1) Supabase Storage > Settings > S3 credentials의 Access/Secret Key를 사용 중인가요?")
        print(" 2) AWS_S3_ENDPOINT_URL이 https://<project>.supabase.co/storage/v1/s3 인가요?")
        print(" 3) 버킷이 존재하고 private/public 설정이 의도대로인가요?")
        print(" 4) 서버/개발환경에서 네트워크/방화벽 제한은 없나요?")
        sys.exit(2)

    if not args.skip_django:
        try_django_storage(prefix=args.prefix)

if __name__ == "__main__":
    main()