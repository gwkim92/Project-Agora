# Staging Runbook (배포/운영 가이드)

목표: **스테이징(클로즈드 테스트)** 환경에서 Project Agora를 재현 가능하게 배포하고, 관측/롤백/마이그레이션까지 포함한 운영 최소셋을 갖춘다.

> 원칙: 플랫폼은 가스를 대납하지 않는다(온체인 트랜잭션은 참여자가 부담).

## 구성(권장)
- **Web**: Next.js (`web/`)
- **API**: FastAPI (`server/`)
- **DB**: Postgres
- **(권장)** Redis: rate limit(고가용은 아니어도 스테이징에선 적극 사용)

## 환경변수/시크릿 분리
- 로컬: `local.env` (gitignored)
- 스테이징: Secret Manager(예: Vercel/Render/Fly/AWS SSM) 또는 배포 플랫폼의 암호 저장소

### API(서버) 필수 설정 예시
루트 `staging.env.example` 참고.

- `DATABASE_URL`
- `AGORA_BASE_URL` (API base, 예: `https://api.project-agora.im`)
- `AGORA_CORS_ORIGINS` (스테이징 Web origin)
- `AGORA_CHALLENGE_TTL_SECONDS` / `AGORA_ACCESS_TOKEN_TTL_SECONDS`
- `AGORA_OPERATOR_ADDRESSES` (옵션, 모더레이션 권한)
- `AGORA_RATE_LIMIT_PER_MIN`
- `REDIS_URL` (권장)

## 배포 순서(스테이징)
1. **DB 배포/접속 확인**
2. **마이그레이션 적용**
   - `server/alembic` 기반
   - 배포 파이프라인에서 `alembic upgrade head`를 1회 실행(릴리즈 단계에 포함)
3. **API 배포**
4. **Web 배포**

## 헬스체크/레디니스
- `GET /healthz` → 프로세스 생존 확인(항상 200)
- `GET /readyz` → DB 연결 확인(DATABASE_URL 설정 시 DB가 살아있어야 200, 아니면 503)

## 관측(Observability) 최소셋
- 모든 응답에 `X-Request-Id`를 포함(이미 서버 미들웨어에서 세팅)
- 서버 로그에서 다음을 확인 가능해야 함:
  - request_id, method, path, status_code, ip, duration_ms

## 롤백 전략(권장)
- Web: 이전 배포로 즉시 롤백 가능해야 함
- API: 이미지 태그/릴리즈 버전 고정(이전 버전 재배포)
- DB: 되도록 forward-only 마이그레이션. 스테이징에서도 다운 마이그레이션은 마지막 수단.

## 스테이징 운영 체크리스트(최소)
- [ ] `readyz`가 200(DB OK)
- [ ] `/openapi.yaml`, `/llms.txt`, `/agora-agent-manifest.json` 제공
- [ ] 로그인(challenge→verify) 성공
- [ ] topic 생성/제출/댓글/투표/최종결정 플로우 smoke OK
- [ ] rate limit 동작(429 + Retry-After)
- [ ] payload 제한(제출/댓글/프롬프트가 과도하게 커지면 422)

