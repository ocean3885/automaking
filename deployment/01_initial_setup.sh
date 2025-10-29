#!/bin/bash
# ============================================================================
# EC2 초기 설정 스크립트 (Ubuntu 24.04 LTS)
# 실행: sudo bash 01_initial_setup.sh
# ============================================================================

set -e  # 에러 발생 시 스크립트 중단

echo "=================================="
echo "EC2 인스턴스 초기 설정 시작"
echo "=================================="

# 1. 시스템 업데이트
echo "[1/7] 시스템 패키지 업데이트..."
apt-get update
apt-get upgrade -y

# 2. 필수 패키지 설치
echo "[2/7] 필수 패키지 설치..."
apt-get install -y \
    python3.12 \
    python3.12-venv \
    python3-pip \
    git \
    nginx \
    supervisor \
    postgresql-client \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    pkg-config \
    curl \
    wget \
    unzip \
    htop \
    vim

# 3. FFmpeg 설치 (pydub 의존성)
echo "[3/7] FFmpeg 설치..."
apt-get install -y ffmpeg

# 4. 프로젝트 디렉토리 생성
echo "[4/7] 프로젝트 디렉토리 생성..."
mkdir -p /var/www/automaking
mkdir -p /var/www/automaking/logs
mkdir -p /var/www/automaking/static
mkdir -p /var/www/automaking/media

# 5. 배포 사용자 생성 (이미 있으면 스킵)
echo "[5/7] 배포 사용자 확인..."
if ! id "ubuntu" &>/dev/null; then
    useradd -m -s /bin/bash ubuntu
    echo "ubuntu ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/ubuntu
    echo "사용자 'ubuntu' 생성 완료"
else
    echo "사용자 'ubuntu' 이미 존재"
fi

# 6. 디렉토리 권한 설정
echo "[6/7] 디렉토리 권한 설정..."
chown -R ubuntu:ubuntu /var/www/automaking
chmod -R 755 /var/www/automaking

# 7. 방화벽 설정 (UFW)
echo "[7/7] 방화벽 설정..."
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw --force enable

echo "=================================="
echo "초기 설정 완료!"
echo "=================================="
echo ""
echo "다음 단계:"
echo "1. 프로젝트 저장소 클론: git clone https://github.com/ocean3885/automaking.git /var/www/automaking"
echo "2. 배포 스크립트 실행: cd /var/www/automaking && bash deployment/02_deploy_app.sh"
echo ""
