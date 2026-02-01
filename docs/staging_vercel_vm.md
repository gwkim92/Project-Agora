# Staging: Vercel(Web) + VM(API) 가이드

## 목표
- Web은 Vercel Preview/Branch 환경으로 배포
- API는 VM(EC2 등)에 Docker로 배포 + Caddy로 HTTPS 종단
- DB/Redis는 **Managed 권장**

---

## 1) 도메인/TLS
1. API 도메인 준비 (예: `api.project-agora.im`)
2. VM 공인 IP로 A 레코드 설정
3. Caddy가 자동으로 Let’s Encrypt TLS를 발급/갱신

---

## 2) VM(API) 배포
리포지토리를 VM에 가져온 뒤:

1. `deploy/staging/env.example`를 참고해 VM 환경변수 준비
2. `deploy/staging/docker-compose.yml`로 실행

구성:
- API: `server/Dockerfile`
- Reverse proxy/TLS: `deploy/staging/Caddyfile`

필수 환경변수:
- `DATABASE_URL` (managed Postgres)
- `AGORA_BASE_URL=https://staging-api...`
- `AGORA_CORS_ORIGINS=https://<vercel-staging-domain>`
- (권장) `REDIS_URL` (rate limit)

---

## 3) Vercel(Web) 환경변수
Vercel 프로젝트(스테이징/프리뷰 환경)에 아래를 설정:
- `NEXT_PUBLIC_AGORA_API_BASE=https://api.project-agora.im`
- `AGORA_COOKIE_SECURE=1`
- `AGORA_COOKIE_SAMESITE=strict` (문제가 있으면 `lax`)

---

## 4) 마이그레이션
릴리즈 시마다(최소 1회) DB에:
- `cd server && alembic upgrade head`

---

## 5) 스모크 테스트
`docs/staging_release.md`의 스모크 체크를 그대로 수행:
- `/healthz`, `/readyz`
- auth(challenge→verify)
- topic/submission/comment/vote/finalize

