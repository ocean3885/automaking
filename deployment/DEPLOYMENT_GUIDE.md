# EC2 배포 가이드

## 📋 목차
1. [사전 준비](#사전-준비)
2. [EC2 인스턴스 초기 설정](#ec2-인스턴스-초기-설정)
3. [애플리케이션 배포](#애플리케이션-배포)
4. [서비스 시작 및 확인](#서비스-시작-및-확인)
5. [HTTPS 설정 (선택사항)](#https-설정)
6. [문제 해결](#문제-해결)
7. [유지보수](#유지보수)

---

## 🚀 사전 준비

### 1. AWS EC2 인스턴스 생성
- **OS**: Ubuntu 24.04 LTS (권장)
- **인스턴스 타입**: t3.medium 이상 (메모리 4GB+)
- **스토리지**: 20GB 이상
- **보안 그룹**: 
  - SSH (22) - 본인 IP만 허용
  - HTTP (80) - 0.0.0.0/0
  - HTTPS (443) - 0.0.0.0/0

### 2. 필수 정보 준비
- ✅ Supabase Database 연결 정보
- ✅ Supabase Storage API Keys (S3 호환)
- ✅ Supabase Service Role Key (프라이빗 버킷용)
- ✅ Google Cloud TTS 서비스 계정 JSON
- ✅ Gemini API Key
- ✅ Django Secret Key (새로 생성)

---

## 🔧 EC2 인스턴스 초기 설정

### 1단계: EC2 접속
```bash
ssh -i "your-key.pem" ubuntu@your-ec2-public-ip
```

### 2단계: 저장소 클론
```bash
cd ~
git clone https://github.com/ocean3885/automaking.git
cd automaking
```

### 3단계: 초기 설정 스크립트 실행
```bash
# root 권한으로 실행
sudo bash deployment/01_initial_setup.sh
```

**이 스크립트가 수행하는 작업:**
- ✅ 시스템 패키지 업데이트
- ✅ Python 3.12, Nginx, Git 설치
- ✅ FFmpeg 설치 (오디오 처리용)
- ✅ 프로젝트 디렉토리 생성 (`/var/www/automaking`)
- ✅ 방화벽 설정 (UFW)

---

## 📦 애플리케이션 배포

### 1단계: 환경 변수 설정
```bash
# 템플릿 복사
cd /var/www/automaking
cp ~/automaking/deployment/.env.production.template ~/automaking/.env.production

# 환경 변수 편집
nano ~/automaking/.env.production
```

**필수 설정 항목:**
1. `SECRET_KEY` - Django 시크릿 키 (새로 생성)
   ```bash
   python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
   ```

2. `ALLOWED_HOSTS` - EC2 퍼블릭 IP 또는 도메인
   ```
   ALLOWED_HOSTS=ec2-xx-xx-xx-xx.compute.amazonaws.com,your-domain.com
   ```

3. Supabase 연결 정보 (Database + Storage)
4. Google Cloud TTS 서비스 계정 정보
5. Gemini API Key

### 2단계: 배포 스크립트 실행
```bash
cd ~/automaking
bash deployment/02_deploy_app.sh
```

**이 스크립트가 수행하는 작업:**
- ✅ Git 저장소 클론/업데이트
- ✅ Python 가상환경 생성
- ✅ 패키지 설치 (requirements.txt)
- ✅ 데이터베이스 마이그레이션
- ✅ 정적 파일 수집
- ✅ Gunicorn & Nginx 설정 복사

---

## ▶️ 서비스 시작 및 확인

### 1단계: Gunicorn 서비스 시작
```bash
# 서비스 시작
sudo systemctl start gunicorn

# 부팅 시 자동 시작 설정
sudo systemctl enable gunicorn

# 상태 확인
sudo systemctl status gunicorn
```

### 2단계: Nginx 시작
```bash
# Nginx 설정 테스트
sudo nginx -t

# Nginx 재시작
sudo systemctl restart nginx

# 상태 확인
sudo systemctl status nginx
```

### 6단계: 관리자 계정 생성
```bash
cd /var/www/automaking
source /var/www/automaking/venv/bin/activate
python manage.py createsuperuser --settings=automaking.settings.production
```

### 4단계: 웹 브라우저에서 확인
```
http://your-ec2-public-ip
http://your-ec2-public-ip/admin
```

---

## 🔒 HTTPS 설정 (Let's Encrypt)

### 1단계: Certbot 설치
```bash
sudo apt-get install -y certbot python3-certbot-nginx
```

### 2단계: 도메인 설정
Nginx 설정 파일 수정:
```bash
sudo nano /etc/nginx/sites-available/automaking
```

`server_name _` 부분을 실제 도메인으로 변경:
```nginx
server_name your-domain.com www.your-domain.com;
```

### 3단계: SSL 인증서 발급
```bash
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

### 4단계: 자동 갱신 설정 (Certbot이 자동으로 설정)
```bash
# 갱신 테스트
sudo certbot renew --dry-run
```

---

## 🔍 문제 해결

### 로그 확인
```bash
# Gunicorn 로그
sudo journalctl -u gunicorn -f

# Django 애플리케이션 로그
tail -f /var/www/automaking/logs/django.log
tail -f /var/www/automaking/logs/gunicorn-error.log

# Nginx 로그
tail -f /var/www/automaking/logs/nginx-error.log
tail -f /var/www/automaking/logs/nginx-access.log
```

### 일반적인 문제

#### 1. "502 Bad Gateway" 오류
```bash
# Gunicorn 소켓 파일 확인
ls -la /var/www/automaking/gunicorn.sock

# Gunicorn 재시작
sudo systemctl restart gunicorn

# 권한 확인
sudo chown ubuntu:www-data /var/www/automaking/gunicorn.sock
```

#### 2. 정적 파일이 로드되지 않음
```bash
# 정적 파일 재수집
cd /var/www/automaking/app
source /var/www/automaking/venv/bin/activate
python manage.py collectstatic --settings=automaking.settings.production --noinput

# 권한 확인
sudo chown -R ubuntu:www-data /var/www/automaking/static
sudo chmod -R 755 /var/www/automaking/static
```

#### 3. 데이터베이스 연결 오류
```bash
# .env.production 확인
cat /var/www/automaking/app/.env.production | grep SUPABASE

# 데이터베이스 연결 테스트
cd /var/www/automaking/app
source /var/www/automaking/venv/bin/activate
python manage.py dbshell --settings=automaking.settings.production
```

#### 4. Supabase Storage 업로드 실패
- ✅ `SUPABASE_SERVICE_ROLE_KEY` 확인
- ✅ Supabase Dashboard에서 버킷이 Private으로 설정되어 있는지 확인
- ✅ S3 Access Keys 유효성 확인

---

## 🔄 유지보수

### 코드 업데이트 (배포)
```bash
cd /var/www/automaking
git pull origin main

# 가상환경 활성화
source /var/www/automaking/venv/bin/activate

# 의존성 업데이트 (필요시)
pip install -r requirements.txt

# 마이그레이션
python manage.py migrate --settings=automaking.settings.production

# 정적 파일 수집
python manage.py collectstatic --settings=automaking.settings.production --noinput

# Gunicorn 재시작
sudo systemctl restart gunicorn
```

### 자동 배포 스크립트
```bash
# deployment/03_update_app.sh 사용
cd /var/www/automaking
bash deployment/03_update_app.sh
```

### 서비스 재시작
```bash
# Gunicorn만 재시작
sudo systemctl restart gunicorn

# Nginx만 재시작
sudo systemctl restart nginx

# 모두 재시작
sudo systemctl restart gunicorn nginx
```

### 백업
```bash
# 데이터베이스 백업 (Supabase Console에서 수행)
# 미디어 파일 백업 (Supabase Storage 자동 백업)

# 로컬 설정 파일 백업
sudo tar -czf automaking-backup-$(date +%Y%m%d).tar.gz \
    /var/www/automaking/.env.production \
    /var/www/automaking/logs/
```

---

## 📊 성능 모니터링

### 시스템 리소스 확인
```bash
# 메모리 사용량
free -h

# 디스크 사용량
df -h

# CPU 사용량
htop

# 프로세스 확인
ps aux | grep gunicorn
```

### Gunicorn Worker 수 조정
```bash
# /etc/systemd/system/gunicorn.service 편집
sudo nano /etc/systemd/system/gunicorn.service

# --workers 값 조정 (권장: CPU 코어 수 * 2 + 1)
# 예: 2코어 EC2 = --workers 5

# 변경 사항 적용
sudo systemctl daemon-reload
sudo systemctl restart gunicorn
```

---

## 🆘 지원

문제가 발생하면:
1. 로그 파일 확인
2. GitHub Issues에 문제 제기
3. 관리자에게 연락

---

## ✅ 배포 체크리스트

- [ ] EC2 인스턴스 생성 및 보안 그룹 설정
- [ ] 초기 설정 스크립트 실행
- [ ] .env.production 파일 설정
- [ ] 배포 스크립트 실행
- [ ] Gunicorn 서비스 시작 및 확인
- [ ] Nginx 서비스 시작 및 확인
- [ ] 관리자 계정 생성
- [ ] Admin에서 UserProfile 생성 및 프리미엄 멤버십 부여
- [ ] Supabase Storage 버킷을 Private으로 설정
- [ ] 웹사이트 접속 테스트
- [ ] HTTPS 설정 (도메인 보유 시)
- [ ] 백업 계획 수립

---

**배포 날짜**: $(date +%Y-%m-%d)  
**버전**: 1.0
