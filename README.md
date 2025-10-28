# AutoMaking

Django 기반 자동 음성 생성 및 학습 서비스

## 환경 설정

이 프로젝트는 환경별로 설정이 분리되어 있습니다:

### 설정 파일 구조

```
automaking/settings/
├── __init__.py
├── base.py          # 공통 설정
├── local.py         # 로컬 개발 환경
└── production.py    # 배포 환경
```

### 로컬 개발 환경

기본적으로 `local.py` 설정을 사용합니다:

```bash
# manage.py는 기본적으로 local 설정을 사용
python manage.py runserver
```

### 배포 환경

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
- PostgreSQL 권장
- 보안 설정 활성화 (HTTPS, HSTS, Secure Cookies)
- 환경 변수로 데이터베이스 설정

### 필수 환경 변수 (Production)

```bash
export DB_NAME=automaking
export DB_USER=automaking_user
export DB_PASSWORD=your_secure_password
export DB_HOST=localhost
export DB_PORT=5432
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

### 3. secret.json 파일 생성

프로젝트 루트에 `secret.json` 파일을 생성하세요:

```json
{
  "SECRET_KEY": "your-secret-key-here",
  "GEMINI_API_KEY": "your-gemini-api-key-here",
  "GOOGLE_CLOUD_CREDENTIALS": {
    "type": "service_account",
    "project_id": "your-project-id",
    ...
  }
}
```

**API 키 발급 방법:**
- Gemini API Key: https://makersuite.google.com/app/apikey
- Google Cloud TTS: https://console.cloud.google.com/apis/credentials

### 4. 데이터베이스 마이그레이션

```bash
python manage.py migrate
```

### 5. 서버 실행

```bash
python manage.py runserver
```

## 기능

- **파일 업로드**: 텍스트 파일 업로드 및 자동 음성 생성 (Google Cloud TTS)
- **AI 문장 생성**: Gemini AI로 학습용 문장 자동 생성
  - 언어 선택 (스페인어, 영어, 프랑스어, 독일어, 일본어, 중국어)
  - 단어/표현 기반 문장 생성
  - 생성 개수 선택 (3~20개)
- 음성 파일 목록 및 검색
- 문장별 동기화 재생
- 재생 속도 조절 (0.5x ~ 1.5x)
- 문장 반복 재생
- 조회수 추적
- 카테고리별 분류

## 기술 스택

- Django 5.2.7
- Django Allauth (인증)
- Google Cloud Text-to-Speech API
- Google Gemini AI (문장 생성)
- Bootstrap 5
- SQLite (개발) / PostgreSQL (배포 권장)
