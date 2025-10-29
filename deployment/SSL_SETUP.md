# SSL/HTTPS 설정 가이드

이 가이드는 Let's Encrypt를 사용하여 무료 SSL 인증서를 발급받고 HTTPS를 설정하는 방법을 설명합니다.

## 🔒 HTTPS가 필요한 이유

1. **보안**: 데이터 암호화로 중간자 공격 방지
2. **Django 설정**: `production.py`의 보안 설정이 HTTPS를 요구
   - `SECURE_SSL_REDIRECT = True`
   - `SESSION_COOKIE_SECURE = True`
   - `CSRF_COOKIE_SECURE = True`
3. **Supabase Storage**: Signed URL은 HTTPS 환경에서 안전하게 작동
4. **SEO**: 검색 엔진이 HTTPS 사이트를 선호

---

## 🚀 빠른 설정 (Let's Encrypt)

### 1단계: Certbot 설치

```bash
sudo apt-get update
sudo apt-get install -y certbot python3-certbot-nginx
```

### 2단계: Nginx 설정 파일 수정

도메인 이름을 실제 도메인으로 변경:

```bash
sudo nano /etc/nginx/sites-available/automaking
```

다음 줄을 수정:
```nginx
server_name _; # 변경 전
↓
server_name your-domain.com www.your-domain.com; # 변경 후
```

### 3단계: Nginx 설정 테스트 및 재시작

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 4단계: SSL 인증서 발급

```bash
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

**질문에 답변:**
- 이메일 입력 (갱신 알림용)
- 약관 동의: Y
- 뉴스레터 구독 (선택사항): Y 또는 N
- HTTPS 리다이렉트: 2 (권장)

### 5단계: 확인

```bash
# 인증서 확인
sudo certbot certificates

# 웹사이트 접속
https://your-domain.com
```

---

## 🔄 자동 갱신 설정

Let's Encrypt 인증서는 **90일** 유효합니다. Certbot이 자동으로 갱신 작업을 설정합니다.

### 갱신 테스트

```bash
sudo certbot renew --dry-run
```

### 자동 갱신 확인

```bash
# systemd 타이머 확인
sudo systemctl status certbot.timer

# 수동 갱신 (필요시)
sudo certbot renew
```

---

## 🧪 HTTPS 없이 테스트하기 (개발용)

도메인이 없거나 테스트 환경에서 HTTPS 없이 배포하려면:

### 1. Django 보안 설정 임시 비활성화

`automaking/settings/production.py` 수정:

```python
# HTTPS 없이 테스트할 때만 False로 변경
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
```

### 2. Nginx에서 HTTP만 사용

이미 `/etc/nginx/sites-available/automaking` 파일에 HTTP와 HTTPS가 모두 설정되어 있습니다.

- **HTTPS 인증서가 없으면**: HTTP(80 포트)로만 동작
- **인증서 발급 후**: 자동으로 HTTPS(443 포트)도 활성화

---

## 🌐 자체 서명 인증서 (테스트용)

Let's Encrypt를 사용할 수 없는 경우 자체 서명 인증서로 테스트:

```bash
# 1. 인증서 생성
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/nginx-selfsigned.key \
  -out /etc/ssl/certs/nginx-selfsigned.crt

# 2. nginx.conf에서 주석 해제 및 경로 수정
sudo nano /etc/nginx/sites-available/automaking
```

주석 처리된 SSL 설정을 활성화하고 경로를 변경:
```nginx
ssl_certificate /etc/ssl/certs/nginx-selfsigned.crt;
ssl_certificate_key /etc/ssl/private/nginx-selfsigned.key;
```

⚠️ **주의**: 자체 서명 인증서는 브라우저에서 경고가 표시됩니다. 프로덕션 환경에서는 사용하지 마세요.

---

## 📊 Nginx 설정 설명

### HTTP → HTTPS 리다이렉트

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # Let's Encrypt 인증서 발급을 위한 경로
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    # 나머지 모든 요청은 HTTPS로
    location / {
        return 301 https://$host$request_uri;
    }
}
```

### HTTPS 서버 블록

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL 인증서
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # 보안 헤더
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    
    # ... 나머지 설정
}
```

### Supabase Storage 최적화

```nginx
# /media/ 경로는 Django에서 signed URL로 처리
# Nginx는 정적 파일만 직접 서빙
location /static/ {
    alias /var/www/automaking/static/;
    expires 30d;
    add_header Cache-Control "public, immutable";
}

# 오디오 생성 타임아웃 설정
location / {
    proxy_connect_timeout 120s;
    proxy_read_timeout 120s;
    # ...
}
```

---

## 🔍 문제 해결

### "Failed to fetch URL" 오류

```bash
# DNS 설정 확인
nslookup your-domain.com

# 도메인이 EC2 IP를 가리키는지 확인
dig your-domain.com +short
```

### Certbot 갱신 실패

```bash
# 로그 확인
sudo tail -f /var/log/letsencrypt/letsencrypt.log

# 수동 갱신 시도
sudo certbot renew --force-renewal
```

### Mixed Content 경고

HTTPS 페이지에서 HTTP 리소스를 로드하면 발생:

```python
# settings/production.py
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
```

---

## ✅ HTTPS 체크리스트

배포 전:
- [ ] 도메인 구입 및 DNS 설정 (EC2 IP 연결)
- [ ] EC2 보안 그룹에서 443 포트 허용
- [ ] Nginx 설정에서 `server_name` 변경

배포 후:
- [ ] Certbot으로 SSL 인증서 발급
- [ ] `https://your-domain.com` 접속 확인
- [ ] SSL Labs에서 보안 등급 테스트 (https://www.ssllabs.com/ssltest/)
- [ ] 자동 갱신 테스트 (`certbot renew --dry-run`)
- [ ] Django 보안 설정 확인

---

## 🎯 권장 설정 (프로덕션)

```bash
# 1. 도메인 구입
# 2. DNS A 레코드 설정: your-domain.com → EC2 IP
# 3. DNS A 레코드 설정: www.your-domain.com → EC2 IP
# 4. EC2 보안 그룹: 443 포트 허용
# 5. Certbot으로 SSL 발급
# 6. HTTP → HTTPS 자동 리다이렉트
# 7. HSTS 활성화 (이미 nginx.conf에 포함)
```

---

## 📚 참고 자료

- Let's Encrypt: https://letsencrypt.org/
- Certbot 문서: https://certbot.eff.org/
- Nginx SSL 설정: https://nginx.org/en/docs/http/configuring_https_servers.html
- Django 보안 설정: https://docs.djangoproject.com/en/stable/topics/security/

---

**보안은 선택이 아닌 필수입니다!** 🔒
