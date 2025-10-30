#!/bin/bash
# ============================================================================
# Django 애플리케이션 배포 스크립트
# 실행: bash 02_deploy_app.sh
# ============================================================================

set -e  # 에러 발생 시 스크립트 중단

# 환경 변수
GITHUB_REPO="https://github.com/ocean3885/automaking.git"
PROJECT_DIR="/var/www/automaking"
VENV_DIR="$PROJECT_DIR/venv"

# SSL 자동 설정 기본값 (원하면 환경변수로 덮어쓸 수 있음)
DOMAIN_DEFAULT="ec2-52-79-212-162.ap-northeast-2.compute.amazonaws.com"
CERTBOT_EMAIL_DEFAULT="ocean3885@gmail.com"

# 외부에서 미리 설정하지 않았다면 기본값으로 설정
export DOMAIN="${DOMAIN:-$DOMAIN_DEFAULT}"
export CERTBOT_EMAIL="${CERTBOT_EMAIL:-$CERTBOT_EMAIL_DEFAULT}"

echo "=================================="
echo "Django 애플리케이션 배포 시작"
echo "=================================="

# 1. Git 저장소 클론 또는 업데이트
echo "[1/12] Git 저장소 클론/업데이트..."
if [ -d "$PROJECT_DIR/.git" ]; then
    echo "기존 저장소 업데이트..."
    cd "$PROJECT_DIR"
    git pull origin main
else
    echo "새로운 저장소 클론..."
    # /var/www 디렉토리 생성 (없을 경우)
    sudo mkdir -p /var/www
    
    # 프로젝트 디렉토리가 존재하지 않으면 바로 클론
    if [ ! -d "$PROJECT_DIR" ]; then
        sudo git clone "$GITHUB_REPO" "$PROJECT_DIR"
        # 클론 후 즉시 소유자 변경
        sudo chown -R ubuntu:ubuntu "$PROJECT_DIR"
    # 디렉토리가 비어있으면 클론 가능
    elif [ -z "$(ls -A $PROJECT_DIR 2>/dev/null)" ]; then
        sudo git clone "$GITHUB_REPO" "$PROJECT_DIR"
        sudo chown -R ubuntu:ubuntu "$PROJECT_DIR"
    # 비어있지 않으면 임시 디렉토리 사용
    else
        echo "  ⚠️  $PROJECT_DIR가 비어있지 않아 임시 디렉토리를 사용합니다..."
        TEMP_DIR=$(mktemp -d)
        git clone "$GITHUB_REPO" "$TEMP_DIR"
        sudo cp -r "$TEMP_DIR"/* "$PROJECT_DIR"/
        sudo chown -R ubuntu:ubuntu "$PROJECT_DIR"
        sudo rm -rf "$TEMP_DIR"
    fi
    cd "$PROJECT_DIR"
fi

# 1.5. 필수 하위 디렉토리 생성
echo "[1.5/12] 프로젝트 하위 디렉토리 생성..."
sudo mkdir -p "$PROJECT_DIR/logs"
sudo mkdir -p "$PROJECT_DIR/media"
sudo mkdir -p "$PROJECT_DIR/static"
# 생성된 디렉토리 소유자 변경
sudo chown -R ubuntu:ubuntu "$PROJECT_DIR/logs" "$PROJECT_DIR/media" "$PROJECT_DIR/static"
echo "✅ logs, media, static 디렉토리 생성 및 권한 설정 완료"

# 2. Python 가상환경 생성
echo "[2/12] Python 가상환경 설정..."
if [ ! -d "$VENV_DIR" ]; then
    python3.12 -m venv "$VENV_DIR"
    echo "가상환경 생성 완료"
else
    echo "기존 가상환경 사용"
fi

# 3. 가상환경 활성화 및 pip 업그레이드
echo "[3/12] pip 업그레이드..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip setuptools wheel

# 4. Python 패키지 설치
echo "[4/12] Python 패키지 설치..."
pip install -r "$PROJECT_DIR/requirements.txt"
pip install gunicorn

# 5. .env.production 파일 확인
echo "[5/12] 환경 변수 파일 확인..."
if [ ! -f "$PROJECT_DIR/.env.production" ]; then
    echo "⚠️  경고: .env.production 파일이 없습니다!"
    echo "📝 템플릿 파일 생성 중..."
    cp "$PROJECT_DIR/deployment/.env.production.template" "$PROJECT_DIR/.env.production"
    echo ""
    echo "❌ .env.production 파일을 편집해야 합니다:"
    echo "   nano $PROJECT_DIR/.env.production"
    echo ""
    read -p "지금 편집하시겠습니까? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        nano "$PROJECT_DIR/.env.production"
    else
        echo "⚠️  배포를 계속하려면 .env.production을 먼저 설정해주세요!"
        exit 1
    fi
else
    echo "✅ .env.production 파일 존재"
fi

# 5.5 환경 변수 로드 (Django 명령 실행을 위해)
echo "[5.5/12] 환경 변수 로드..."
if [ -f "$PROJECT_DIR/.env.production" ]; then
    # .env.production의 환경 변수를 현재 쉘에 export
    set -a  # 모든 변수를 자동으로 export
    source "$PROJECT_DIR/.env.production"
    set +a  # auto export 해제
    echo "✅ 환경 변수 로드 완료"
else
    echo "⚠️  .env.production 파일을 찾을 수 없어 환경 변수를 로드하지 못했습니다."
fi

# 6. Django 설정 확인
echo "[6/12] Django 설정 확인..."
export DJANGO_SETTINGS_MODULE=automaking.settings.production
python "$PROJECT_DIR/manage.py" check --settings=automaking.settings.production

# 7. 데이터베이스 마이그레이션
echo "[7/12] 데이터베이스 마이그레이션..."
python "$PROJECT_DIR/manage.py" migrate --settings=automaking.settings.production --noinput

# 8. 정적 파일 수집
echo "[8/12] 정적 파일 수집..."
python "$PROJECT_DIR/manage.py" collectstatic --settings=automaking.settings.production --noinput

# 9. 권한 설정
echo "[9/12] 파일 권한 설정..."
sudo chown -R ubuntu:www-data "$PROJECT_DIR"
sudo chmod -R 755 "$PROJECT_DIR"
sudo chmod -R 775 "$PROJECT_DIR/logs"
sudo chmod -R 775 "$PROJECT_DIR/media"

# 10. Gunicorn 및 Nginx 설정 복사
echo "[10/12] 서비스 설정 파일 복사..."
sudo cp "$PROJECT_DIR/deployment/gunicorn.service" /etc/systemd/system/
sudo cp "$PROJECT_DIR/deployment/nginx.conf" /etc/nginx/sites-available/automaking
sudo ln -sf /etc/nginx/sites-available/automaking /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Nginx 설정 테스트
echo "Nginx 설정 테스트..."
sudo nginx -t

echo "[11/12] Certbot 및 SSL 설정 (옵션)..."
echo "  - DOMAIN=${DOMAIN} (환경변수로 덮어쓰기 가능)"
echo "  - CERTBOT_EMAIL=${CERTBOT_EMAIL} (환경변수로 덮어쓰기 가능)"

# 도메인과 이메일은 환경 변수 또는 .env.production에서 읽을 수 있습니다
# 우선순위: 스크립트 환경변수 > .env.production 값

DOMAIN_ENV="${DOMAIN:-}"
EMAIL_ENV="${CERTBOT_EMAIL:-}"

# .env.production에서 ALLOWED_HOSTS 첫 번째 값을 도메인으로 추출 (콤마 구분)
if [ -z "$DOMAIN_ENV" ] && [ -f "$PROJECT_DIR/.env.production" ]; then
    DOMAIN_ENV=$(grep -E '^ALLOWED_HOSTS=' "$PROJECT_DIR/.env.production" | sed 's/ALLOWED_HOSTS=//' | cut -d',' -f1)
fi

if [ -n "$DOMAIN_ENV" ] && [ -n "$EMAIL_ENV" ]; then
    echo "도메인: $DOMAIN_ENV"
    echo "인증서 이메일: $EMAIL_ENV"
    echo "Certbot 설치 및 인증서 발급을 시도합니다..."

    # Certbot 설치 (Ubuntu/Debian)
    if ! command -v certbot >/dev/null 2>&1; then
        echo "certbot이 없어 설치합니다..."
        sudo apt-get update
        sudo apt-get install -y certbot python3-certbot-nginx
    fi

    # 방화벽(UFW) 사용 시 Nginx Full 허용 (무시 가능)
    if command -v ufw >/dev/null 2>&1; then
        sudo ufw allow 'Nginx Full' || true
    fi

    # Nginx 설정 테스트 후 Certbot으로 인증서 발급
    sudo nginx -t && sudo systemctl reload nginx
    sudo certbot --nginx -d "$DOMAIN_ENV" --agree-tos -m "$EMAIL_ENV" --non-interactive --redirect || {
        echo "⚠️  Certbot 발급 실패. SSL은 수동으로 설정해야 할 수 있습니다."
    }

    # 자동 갱신 테스트
    sudo certbot renew --dry-run || true
else
    echo "⚠️  SSL 자동 설정 건너뜀: DOMAIN 또는 CERTBOT_EMAIL이 설정되지 않았습니다."
    echo "    DOMAIN 환경변수 또는 .env.production의 ALLOWED_HOSTS 첫 값, 그리고 CERTBOT_EMAIL을 설정하면 자동으로 인증서를 발급합니다."
fi

echo "[12/12] 요약 및 다음 단계"
echo "=================================="
echo "배포 완료!"
echo "=================================="
echo ""
echo "다음 단계:"
echo "1. 서비스 시작: sudo systemctl start gunicorn"
echo "2. 서비스 활성화: sudo systemctl enable gunicorn"
echo "3. Nginx 재시작: sudo systemctl restart nginx"
echo "4. 상태 확인: sudo systemctl status gunicorn"
echo ""
echo "관리자 계정 생성 (선택사항):"
echo "  cd $PROJECT_DIR"
echo "  source $VENV_DIR/bin/activate"
echo "  python manage.py createsuperuser --settings=automaking.settings.production"
echo ""
echo "로그 확인:"
echo "  sudo journalctl -u gunicorn -f"
echo "  tail -f $PROJECT_DIR/logs/django.log"
echo ""
