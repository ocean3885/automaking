#!/bin/bash
# ============================================================================
# Django Superuser 생성 스크립트
# 실행: bash deployment/create_superuser.sh
# ============================================================================

set -e

PROJECT_DIR="/var/www/automaking"
VENV_DIR="$PROJECT_DIR/venv"

echo "=================================="
echo "Django Superuser 생성"
echo "=================================="

# 1. 프로젝트 디렉토리로 이동
cd "$PROJECT_DIR"

# 2. 가상환경 활성화
echo "[1/3] 가상환경 활성화..."
source "$VENV_DIR/bin/activate"

# 3. 환경변수 로드
echo "[2/3] 환경변수 로드..."
if [ -f "$PROJECT_DIR/.env.production" ]; then
    set -a
    source "$PROJECT_DIR/.env.production"
    set +a
    echo "✅ 환경변수 로드 완료"
else
    echo "❌ .env.production 파일을 찾을 수 없습니다!"
    exit 1
fi

# 4. Superuser 생성
echo "[3/3] Superuser 생성..."
export DJANGO_SETTINGS_MODULE=automaking.settings.production
python manage.py createsuperuser --settings=automaking.settings.production

echo ""
echo "✅ Superuser 생성 완료!"
echo ""
echo "Admin 페이지 접속:"
echo "  http://lang.ai.kr/admin/"