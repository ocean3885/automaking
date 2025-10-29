# AutoMaking

Django 기반 자동 음성 생성 및 학습 서비스

## 주요 특징

- ✨ **AI 문장 생성**: Google Gemini AI로 다국어 학습 문장 자동 생성
- 🎙️ **음성 합성**: Google Cloud Text-to-Speech로 자연스러운 음성 생성
- 📚 **보관함 시스템**: 유저별 맞춤 보관함으로 콘텐츠 관리
- 🎯 **고급 플레이어**: 문장별 재생, 속도 조절, 반복 학습 기능
- 🔐 **완전한 인증**: Django Allauth 기반 회원가입/로그인
- 🚀 **Production Ready**: Supabase PostgreSQL + `.env` 기반 환경 관리

## 환경 설정

이 프로젝트는 환경별로 설정이 분리되어 있으며, **모든 비밀 정보는 `.env` 파일**로 관리됩니다.

### 설정 파일 구조

```
automaking/settings/
├── __init__.py
├── base.py          # 공통 설정
├── local.py         # 로컬 개발 환경
└── production.py    # 배포 환경 (Supabase PostgreSQL)
```

### 로컬 개발 환경

기본적으로 `local.py` 설정을 사용합니다:

```bash
# manage.py는 기본적으로 local 설정을 사용
python manage.py runserver
```

### 배포 환경 (Supabase)

배포 시에는 환경 변수로 설정을 지정하세요:

```bash
export DJANGO_SETTINGS_MODULE=automaking.settings.production
python manage.py runserver
```

또는 Gunicorn 사용 시:

```bash
gunicorn automaking.wsgi:application --env DJANGO_SETTINGS_MODULE=automaking.settings.production
```

### 환경별 설정 사항

#### Local (개발)
- DEBUG = True
- SQLite 데이터베이스
- ALLOWED_HOSTS = ['*']

#### Production (배포)
- DEBUG = False
- Supabase PostgreSQL (SSL 필수)
- 보안 설정 활성화 (HTTPS, HSTS, Secure Cookies)
- 환경 변수로 데이터베이스 설정

### Supabase 데이터베이스 설정

#### 1. Supabase 프로젝트 생성
1. [Supabase](https://supabase.com)에 접속하여 프로젝트 생성
2. Project Settings > Database로 이동
3. Connection String 정보 확인

#### 2. 환경 변수 설정

`.env` 파일을 생성하거나 시스템 환경 변수로 설정:

```bash
# Supabase Database 연결 정보
export SUPABASE_DB_NAME=postgres
export SUPABASE_DB_USER=postgres
export SUPABASE_DB_PASSWORD=your-supabase-password
export SUPABASE_DB_HOST=db.xxxxxxxxxxxxx.supabase.co
export SUPABASE_DB_PORT=5432

# Django 설정
export DJANGO_SETTINGS_MODULE=automaking.settings.production
export ALLOWED_HOSTS=your-domain.com,www.your-domain.com
```

**Connection String 예시:**
```
postgresql://postgres:[PASSWORD]@db.xxxxxxxxxxxxx.supabase.co:5432/postgres
```

위 정보를 각각의 환경 변수로 분리하여 설정하세요.

#### 3. psycopg2 설치

PostgreSQL 연결을 위해 필요합니다 (이미 requirements.txt에 포함):

```bash
pip install psycopg2-binary
```

#### 4. 데이터베이스 마이그레이션

```bash
# Production 설정으로 마이그레이션 실행
export DJANGO_SETTINGS_MODULE=automaking.settings.production
python manage.py migrate
```

#### 5. Supabase 보안 규칙 (선택사항)

Supabase의 Row Level Security(RLS)를 사용하려면:
- Supabase Dashboard > Authentication > Policies에서 설정
- Django에서는 일반적으로 애플리케이션 레벨에서 권한 관리

### 필수 환경 변수 (.env.example 참조)

```bash
# Django
DJANGO_SETTINGS_MODULE=automaking.settings.production
SECRET_KEY=your-django-secret-key

# Supabase Database
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=postgres
SUPABASE_DB_PASSWORD=your-password
SUPABASE_DB_HOST=db.xxxxxxxxxxxxx.supabase.co
SUPABASE_DB_PORT=5432

# 도메인
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
```

## 설치 및 실행

### 1. 가상환경 생성 및 활성화

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate  # Windows
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 환경 변수 설정

`.env` 파일을 프로젝트 루트에 생성하세요 (`.env.example` 참고):

```bash
# Django Secret Key 생성
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# .env 파일 생성
cp .env.example .env
# 생성된 .env 파일을 편집하여 실제 값을 입력하세요
```

**필수 환경 변수:**
- `SECRET_KEY`: Django 보안 키
- `GEMINI_API_KEY`: [Google AI Studio](https://makersuite.google.com/app/apikey)에서 발급
- `GOOGLE_CLOUD_*`: [Google Cloud Console](https://console.cloud.google.com/apis/credentials)에서 서비스 계정 생성 후 JSON 키 다운로드

**Supabase 데이터베이스 (Production):**
- `SUPABASE_DB_*`: Supabase Dashboard > Project Settings > Database > Connection String 참고

> **참고:** 이전에 `secret.json` 파일을 사용했다면, `.env` 파일로 마이그레이션한 후 `secret.json`은 삭제하거나 백업하세요. 이제 모든 환경 변수는 `.env` 파일에서 관리됩니다.

### 4. 데이터베이스 마이그레이션

**로컬 개발:**
```bash
python manage.py migrate
```

**배포 (Supabase):**
```bash
export DJANGO_SETTINGS_MODULE=automaking.settings.production
python manage.py migrate
```

### 5. 서버 실행

**로컬:**
```bash
python manage.py runserver
```

**배포:**
```bash
gunicorn automaking.wsgi:application --bind 0.0.0.0:8000
```

## 기능

- **파일 업로드**: 텍스트 파일 업로드 및 자동 음성 생성 (Google Cloud TTS)
- **AI 문장 생성**: Gemini AI로 학습용 문장 자동 생성
  - 언어 선택 (스페인어, 영어, 프랑스어, 독일어, 일본어, 중국어)
  - 단어/표현 기반 문장 생성
  - 생성 개수 선택 (3~20개)
- **보관함 시스템**: 유저별 보관함 생성 및 게시물 관리
  - 본인 및 타인 게시물 모두 추가 가능
  - 보관함별 분류 및 관리
- 음성 파일 목록 및 검색
- 문장별 동기화 재생
- 재생 속도 조절 (0.5x ~ 1.5x)
- 문장 반복 재생
- 조회수 추적
- 카테고리별 분류
- Staff 전용 카테고리 생성 기능

## 기술 스택

- Django 5.2.7
- Django Allauth (인증)
- Supabase PostgreSQL (배포 환경)
- Google Cloud Text-to-Speech API
- Google Gemini AI (문장 생성)
- Bootstrap 5
- SQLite (개발) / PostgreSQL (배포)

## 배포 체크리스트

### Supabase 설정
- [ ] Supabase 프로젝트 생성
- [ ] Database 연결 정보 확인
- [ ] 환경 변수 설정
- [ ] 마이그레이션 실행

### Django 설정
- [ ] SECRET_KEY 변경
- [ ] ALLOWED_HOSTS 설정
- [ ] DEBUG = False 확인
- [ ] Static files 수집 (`python manage.py collectstatic`)
- [ ] HTTPS 설정 (SSL/TLS)

### API 키 설정
- [ ] Google Cloud TTS API 키 (.env 파일에 설정)
- [ ] Gemini API 키 (.env 파일에 설정)

### 보안
- [ ] .env 파일 .gitignore에 추가 (이미 추가됨)
- [ ] 환경 변수로 민감 정보 관리
- [ ] SECRET_KEY 변경
- [ ] CSRF/XSS 보호 활성화
- [ ] HSTS 설정 확인

## 🚀 EC2 배포

빈 EC2 인스턴스에 배포하는 방법은 [deployment/QUICKSTART.md](deployment/QUICKSTART.md)를 참고하세요.

### 빠른 배포 (5단계)

1. **초기 설정** (root 권한)
   ```bash
   git clone https://github.com/ocean3885/automaking.git
   cd automaking
   sudo bash deployment/01_initial_setup.sh
   ```

2. **환경 변수 설정**
   ```bash
   cp deployment/.env.production.template .env.production
   nano .env.production  # 필수 설정 입력
   ```

3. **애플리케이션 배포**
   ```bash
   bash deployment/02_deploy_app.sh
   ```

4. **서비스 시작**
   ```bash
   sudo systemctl start gunicorn
   sudo systemctl enable gunicorn
   sudo systemctl restart nginx
   ```

5. **관리자 계정 생성**
   ```bash
   cd /var/www/automaking
   source /var/www/automaking/venv/bin/activate
   python manage.py createsuperuser --settings=automaking.settings.production
   ```

### 재배포 (업데이트)
```bash
cd /var/www/automaking
bash deployment/03_update_app.sh
```

상세한 배포 가이드:
- 📖 [빠른 시작 가이드](deployment/QUICKSTART.md)
- 📚 [상세 배포 가이드](deployment/DEPLOYMENT_GUIDE.md)

---