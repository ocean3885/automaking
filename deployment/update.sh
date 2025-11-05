#!/bin/bash
# ============================================================================
# Django 애플리케이션 업데이트 스크립트 (재배포용)
# 실행: bash 03_update_app.sh
# ============================================================================

set -e  # 에러 발생 시 스크립트 중단

# 환경 변수
PROJECT_DIR="/var/www/automaking"
VENV_DIR="$PROJECT_DIR/venv"

echo "=================================="
echo "애플리케이션 업데이트 시작"
echo "=================================="

# 1. Git 업데이트
echo "[1/6] Git 저장소 업데이트..."
cd "$PROJECT_DIR"
git pull origin main

# 2. 가상환경 활성화
echo "[2/6] 가상환경 활성화..."
source "$VENV_DIR/bin/activate"

# 3. 환경 변수 로드
echo "[3/6] 환경 변수 로드..."
if [ -f "$PROJECT_DIR/.env.production" ]; then
    set -a
    source "$PROJECT_DIR/.env.production"
    set +a
    echo "✅ 환경 변수 로드 완료"
else
    echo "⚠️  .env.production 파일을 찾을 수 없습니다."
fi

# 4. 패키지 업데이트
echo "[4/6] Python 패키지 업데이트..."
pip install -r "$PROJECT_DIR/requirements.txt" --upgrade

# 5. 마이그레이션
echo "[5/6] 데이터베이스 마이그레이션..."
export DJANGO_SETTINGS_MODULE=automaking.settings.production
python "$PROJECT_DIR/manage.py" migrate --settings=automaking.settings.production --noinput

# 6. Tailwind CSS 프로덕션 빌드 (새로 추가된 단계)
echo "[6/7] Tailwind CSS 프로덕션 빌드 (CSS 최적화)..." # 단계 번호 수정
# settings를 지정하지 않으면 DJANGO_SETTINGS_MODULE 변수를 따라갑니다.
python "$PROJECT_DIR/manage.py" tailwind build
echo "✅ Tailwind CSS 빌드 완료 (Purging 및 Minifying 포함)"

# 7. 정적 파일 수집
echo "[6/6] 정적 파일 수집..."
python "$PROJECT_DIR/manage.py" collectstatic --settings=automaking.settings.production --noinput

# 8. 서비스 재시작
echo "[7/7] Gunicorn 재시작..."
sudo systemctl restart gunicorn

# 상태 확인
sleep 2
if sudo systemctl is-active --quiet gunicorn; then
    echo "=================================="
    echo "✅ 업데이트 완료!"
    echo "=================================="
    echo ""
    echo "서비스 상태:"
    sudo systemctl status gunicorn --no-pager -l
else
    echo "=================================="
    echo "❌ Gunicorn 재시작 실패!"
    echo "=================================="
    echo ""
    echo "로그 확인:"
    echo "  sudo journalctl -u gunicorn -n 50"
    exit 1
fi
