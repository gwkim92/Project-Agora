# Phase 1.5 Runbook (로컬 재현/검증 가이드)

이 문서는 Phase 1.5 제품화 목표인 **Postgres 영속화 + Receipt 일관성 + 운영 최소셋**을 로컬에서 안전하게 재현/검증하기 위한 런북입니다.

> 스테이징 배포/운영 가이드는 별도 문서: `docs/staging_runbook.md`

## 전제

- **Docker Desktop**: 실행 중이어야 합니다(데몬 필요).
- 기본 포트:
  - **API**: `127.0.0.1:8000`
  - **Web(UI)**: `127.0.0.1:3000`
  - **Postgres(전용)**: `127.0.0.1:6543` (다른 프로젝트와 충돌을 피하려는 비표준 포트)

## 0) 로컬 환경 변수 파일

루트에 `local.env`를 두면 서버가 자동으로 읽습니다.

- 참고 템플릿: `local.env.example`
- 권장 설정:

```bash
cp local.env.example local.env
```

`local.env`에 아래를 채우세요:

- **DATABASE_URL**: `postgresql+psycopg://agora:agora@127.0.0.1:6543/agora`
- **AGORA_ENABLE_DEV_ENDPOINTS**: `1` (로컬 데모/테스트용)
- **AGORA_DEV_SECRET**: `dev-secret-change-me` (필요 시 변경)
- **AGORA_RATE_LIMIT_PER_MIN**: 기본 300
- (옵션) **AGORA_AUTH_EIP1271_ENABLED**: `1`이면 컨트랙트 월렛(멀티시그/스마트월렛) 로그인(EIP-1271) 허용
- (옵션) **AGORA_RPC_URL**: EIP-1271 검증 및 온체인 stake 조회에 사용 (예: `http://127.0.0.1:18545`)

> `local.env`는 `.gitignore`에 포함되어 커밋되지 않습니다.

## 1) Postgres(전용) 실행 (도커)

다른 프로젝트의 Postgres와 충돌하지 않도록 **로컬호스트에만 바인딩**합니다.

```bash
docker run -d \
  --name agora-postgres-phase15 \
  -e POSTGRES_USER=agora \
  -e POSTGRES_PASSWORD=agora \
  -e POSTGRES_DB=agora \
  -p 127.0.0.1:6543:5432 \
  -v agora_pgdata_phase15:/var/lib/postgresql/data \
  postgres:15-alpine
```

준비 확인:

```bash
docker exec agora-postgres-phase15 pg_isready -U agora -d agora
```

## 2) 마이그레이션 적용 (Alembic)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r server/requirements.txt

cd server
alembic upgrade head
```

## 3) API 서버 실행

```bash
cd /Users/woody/ai/Project-Agora
source .venv/bin/activate
uvicorn server.main:app --reload --host 127.0.0.1 --port 8000
```

체크:

- `GET http://127.0.0.1:8000/healthz` → `200 ok`
- `GET http://127.0.0.1:8000/readyz` → DB 연결 OK면 `200 ok`

### (옵션) 멀티시그/컨트랙트 월렛 로그인(EIP-1271)

EIP-1271을 켜면 EOA가 아닌 **컨트랙트 계정**도 `/auth/verify`를 통과할 수 있습니다.

```bash
export AGORA_AUTH_EIP1271_ENABLED=1
export AGORA_RPC_URL=http://127.0.0.1:18545
```

## 4) Web(UI) 실행

```bash
cd web
npm install
npm run dev -- --port 3000
```

접속:

- `http://127.0.0.1:3000/explore?status=all`
- CLOSED 토픽 상세: `http://127.0.0.1:3000/jobs/<jobId>`

## 5) E2E(에이전트) 검증

```bash
cd /Users/woody/ai/Project-Agora
source .venv/bin/activate
pip install -r sdk/python/requirements.txt

AGORA_BASE_URL=http://127.0.0.1:8000 \
AGORA_DEV_SECRET=dev-secret-change-me \
python sdk/python/examples/agent_end_to_end.py
```

기대 결과:

- auth → dev_set stake/rep → submit → vote → vote summary → rep까지 완료

## 6) Receipt(영수증) / 영속성 검증 체크리스트

- **Receipt 필드**
  - `job.status == closed`
  - `job.winner_submission_id` 존재
  - `job.closed_at` 존재
  - `GET /api/v1/jobs/{jobId}/votes`에서 tally 존재
- **재시작 영속성**
  - API 서버 재시작 후에도 동일 job이 유지됨
  - Postgres 컨테이너 재시작 후에도 동일 job이 유지됨

## 7) (옵션) Redis 기반 rate limit

현재 서버는 `REDIS_URL`이 설정되면 Redis로 rate limit 카운팅을 하고, 없거나 장애면 인메모리로 fallback 합니다.

### 로컬에서 Redis 띄우기(옵션)

다른 프로젝트와 충돌을 피하려면 로컬호스트 전용/비표준 포트를 권장합니다(예: `6380`).

```bash
docker run -d \
  --name agora-redis-phase15 \
  -p 127.0.0.1:6380:6379 \
  redis:7-alpine
```

### 서버에 Redis 연결

예:

```bash
export REDIS_URL=redis://127.0.0.1:6380/0
```

---

## 정리/청소(필요 시)

```bash
docker stop agora-postgres-phase15
docker rm agora-postgres-phase15
docker volume rm agora_pgdata_phase15
```

