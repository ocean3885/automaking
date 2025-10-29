# 🚀 빠른 시작 가이드

EC2 인스턴스에 Automaking 프로젝트를 배포하는 빠른 가이드입니다.

## 📝 사전 준비
- AWS EC2 인스턴스 (Ubuntu 24.04 LTS)
- Supabase 프로젝트 (Database + Storage)
- Google Cloud TTS 서비스 계정
- Gemini API Key

---

## ⚡ 빠른 배포 (5단계)

### 1️⃣ EC2 접속 및 저장소 클론
```bash
ssh -i "your-key.pem" ubuntu@your-ec2-ip
git clone https://github.com/ocean3885/automaking.git
cd automaking
```

### 2️⃣ 초기 서버 설정 (root 권한 필요)
```bash
sudo bash deployment/01_initial_setup.sh
```
⏱️ 약 5-10분 소요

### 3️⃣ 환경 변수 설정
```bash
# 템플릿 복사
cp deployment/.env.production.template .env.production

# 편집 (필수!)
nano .env.production
```

**최소 설정 항목:**
- `SECRET_KEY` - 새로 생성
- `ALLOWED_HOSTS` - EC2 IP 또는 도메인
- Supabase Database 연결 정보
- Supabase Storage API Keys
- Google Cloud TTS 정보
- Gemini API Key

### 4️⃣ 애플리케이션 배포
```bash
bash deployment/02_deploy_app.sh
```
⏱️ 약 10-15분 소요

### 5️⃣ 서비스 시작
```bash
# Gunicorn 시작
sudo systemctl start gunicorn
sudo systemctl enable gunicorn

# Nginx 재시작
sudo systemctl restart nginx

# 관리자 계정 생성
cd /var/www/automaking
source /var/www/automaking/venv/bin/activate
python manage.py createsuperuser --settings=automaking.settings.production
```

---

## ✅ 확인

웹 브라우저에서 접속:
```
http://your-ec2-public-ip
http://your-ec2-public-ip/admin
```

---

## 🔄 업데이트 (재배포)

코드 변경 후 업데이트:
```bash
cd /var/www/automaking
bash deployment/03_update_app.sh
```

---

## 🆘 문제 해결

### 로그 확인
```bash
# Gunicorn 로그
sudo journalctl -u gunicorn -f

# Django 로그
tail -f /var/www/automaking/logs/django.log

# Nginx 로그
tail -f /var/www/automaking/logs/nginx-error.log
```

### 서비스 재시작
```bash
sudo systemctl restart gunicorn
sudo systemctl restart nginx
```

### 상태 확인
```bash
sudo systemctl status gunicorn
sudo systemctl status nginx
```

---

## 📚 상세 문서

자세한 내용은 [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)를 참고하세요.

---

## 🔐 보안 체크리스트

- [ ] `.env.production` 파일 권한 확인 (600)
- [ ] SSH 포트 22는 본인 IP만 허용
- [ ] EC2 보안 그룹 설정 확인
- [ ] Supabase Storage를 Private 버킷으로 설정
- [ ] Django `SECRET_KEY` 변경
- [ ] `DEBUG=False` 확인
- [ ] HTTPS 설정 (도메인 보유 시)

---

**예상 배포 시간**: 20-30분  
**난이도**: ⭐⭐⭐☆☆
