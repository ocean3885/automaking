# 📦 Deployment Files

EC2 인스턴스 배포를 위한 모든 필수 파일이 포함되어 있습니다.

## 📂 파일 구조

```
deployment/
├── 01_initial_setup.sh          # 초기 서버 설정 스크립트 (root 권한)
├── 02_deploy_app.sh             # 애플리케이션 배포 스크립트
├── 03_update_app.sh             # 업데이트/재배포 스크립트
├── .env.production.template     # 환경 변수 템플릿
├── gunicorn.service             # Gunicorn systemd 서비스 파일
├── nginx.conf                   # Nginx 설정 파일
├── QUICKSTART.md                # 빠른 시작 가이드 ⭐
├── DEPLOYMENT_GUIDE.md          # 상세 배포 가이드 📚
└── README.md                    # 이 파일
```

## 🚀 빠른 시작

### 1️⃣ EC2 접속 및 준비
```bash
ssh -i "your-key.pem" ubuntu@your-ec2-ip
git clone https://github.com/ocean3885/automaking.git
cd automaking
```

### 2️⃣ 초기 설정 (root 권한)
```bash
sudo bash deployment/01_initial_setup.sh
```

### 3️⃣ 환경 변수 설정
```bash
cp deployment/.env.production.template .env.production
nano .env.production
```

### 4️⃣ 애플리케이션 배포
```bash
bash deployment/02_deploy_app.sh
```

### 5️⃣ 서비스 시작
```bash
sudo systemctl start gunicorn
sudo systemctl enable gunicorn
sudo systemctl restart nginx
```

## 📖 문서

- **[QUICKSTART.md](QUICKSTART.md)** - 5단계로 빠르게 배포하기
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - 상세한 배포 가이드 및 문제 해결

## 🔧 스크립트 설명

### `01_initial_setup.sh`
- 시스템 패키지 업데이트
- Python 3.12, Nginx, FFmpeg 설치
- 프로젝트 디렉토리 생성
- 방화벽 설정

### `02_deploy_app.sh`
- Git 저장소 클론/업데이트
- Python 가상환경 생성
- 패키지 설치
- 데이터베이스 마이그레이션
- 정적 파일 수집
- 서비스 설정 복사

### `03_update_app.sh`
- Git pull
- 패키지 업데이트
- 마이그레이션
- 정적 파일 재수집
- Gunicorn 재시작

## ⚙️ 설정 파일

### `gunicorn.service`
- Systemd 서비스 정의
- 3개의 워커 프로세스
- Unix 소켓 통신
- 자동 재시작 설정

### `nginx.conf`
- 리버스 프록시 설정
- 정적/미디어 파일 서빙
- gzip 압축
- 보안 헤더

### `.env.production.template`
- 모든 필수 환경 변수 템플릿
- Supabase Database 연결
- Supabase Storage (S3)
- Google Cloud TTS
- Gemini API

## 🔄 업데이트

### 코드 변경 후:
```bash
cd /var/www/automaking
bash deployment/03_update_app.sh
```

## 🆘 로그 확인

```bash
# Gunicorn
sudo journalctl -u gunicorn -f

# Django
tail -f /var/www/automaking/logs/django.log

# Nginx
tail -f /var/www/automaking/logs/nginx-error.log
```

## 📊 디렉토리 구조 (배포 후)

```
/var/www/automaking/
├── automaking/             # Django 프로젝트 설정
├── core/                   # Django 앱
├── templates/              # 템플릿 파일
├── deployment/             # 배포 스크립트
├── venv/                   # Python 가상환경
├── static/                 # 정적 파일 (collectstatic 결과)
├── media/                  # 미디어 파일 (로컬 저장 시)
├── logs/                   # 로그 파일
│   ├── django.log
│   ├── gunicorn-access.log
│   ├── gunicorn-error.log
│   ├── nginx-access.log
│   └── nginx-error.log
├── gunicorn.sock          # Unix 소켓
├── manage.py              # Django 관리 스크립트
├── requirements.txt       # Python 패키지
├── .env.production        # 환경 변수 (Git 무시)
└── db.sqlite3             # SQLite (로컬 개발용)
```

## ✅ 체크리스트

배포 전:
- [ ] EC2 인스턴스 생성 (Ubuntu 24.04)
- [ ] 보안 그룹 설정 (SSH, HTTP, HTTPS)
- [ ] Supabase 프로젝트 준비
- [ ] API 키 준비 (Google Cloud, Gemini)

배포 후:
- [ ] 웹사이트 접속 확인
- [ ] Admin 페이지 접속 확인
- [ ] 관리자 계정 생성
- [ ] UserProfile 생성 및 프리미엄 부여
- [ ] 파일 업로드 테스트
- [ ] Supabase Storage 연동 확인

## 🔐 보안

- `.env.production` 파일 권한: `600`
- SSH 키 관리 철저
- EC2 보안 그룹 설정
- HTTPS 설정 권장 (Let's Encrypt)

---

**문제가 있나요?** [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)의 문제 해결 섹션을 참고하세요.
