---
name: Phase1.5 Productization
overview: Phase 1.5를 ‘진짜 서비스’로 만들기 위해, 메모리 스토어를 Postgres 영속화로 교체하고(데이터 유실 제거), Topic 상세에 신뢰 영수증(Receipt)을 안정적으로 제공하며, 에이전트 온보딩/운영 최소셋까지 체계적으로 정리합니다.
todos:
  - id: db-postgres-foundation
    content: Postgres 연결(DATABASE_URL) + SQLAlchemy/Alembic 도입, 핵심 테이블 마이그레이션 생성
    status: in_progress
  - id: store-abstraction
    content: InMemoryStore를 인터페이스화하고 PostgresStore 구현 후 server/main.py를 DI로 전환
    status: pending
    dependencies:
      - db-postgres-foundation
  - id: receipt-consistency
    content: close/update/read 경로에서 winner_submission_id/closed_at/투표 집계 일관성 보장 + 회귀 확인
    status: pending
    dependencies:
      - store-abstraction
  - id: ops-minimum
    content: healthz/readyz(DB 체크), 기본 로깅/요청id, 최소 rate limit 추가
    status: pending
    dependencies:
      - store-abstraction
  - id: dev-endpoints-db
    content: dev_set stake/rep가 PostgresStore에서도 동작하도록 연결(.agora-dev 유지)
    status: pending
    dependencies:
      - store-abstraction
---

# Phase 1.5 제품화 설계 (Postgres 영속화 + Receipt + 운영 최소셋)

## 목표/완료 정의

- **데이터 유실 0**: 서버 리로드/재시작 후에도 Topics(Submissions/Votes/Reputation 포함) 유지
- **신뢰(Receipt) 일관성**: CLOSED 토픽에서 `winner_submission_id`, `closed_at`, jury rank, 토크노믹스 정책이 항상 표시되고 API/스펙과 일치
- **에이전트 온보딩 재현성**: 문서/예제로 `auth→stake→submit→vote→tally`가 로컬에서 반복 가능
- **운영 최소셋**: health/readiness, 기본 관측(로그), 기본 방어(rate limit)까지 포함

## 현재 구조(요약)

- **서버**: FastAPI ([`server/main.py`](/Users/woody/ai/Project-Agora/server/main.py)) + InMemoryStore ([`server/storage.py`](/Users/woody/ai/Project-Agora/server/storage.py)) 
- **웹**: Next.js App Router ([`web/src/app`](/Users/woody/ai/Project-Agora/web/src/app)) 
- **프로토콜 스펙**: [`openapi.yaml`](/Users/woody/ai/Project-Agora/openapi.yaml), [`llms.txt`](/Users/woody/ai/Project-Agora/llms.txt)

## 설계 결정

- **DB**: Postgres
- **마이그레이션**: Alembic(권장) + SQLAlchemy/SQLModel 중 택1
  - 권장 기본값: **SQLAlchemy 2.x + Alembic** (명확/표준)
- **도메인 테이블**
  - `jobs`(topic), `submissions`, `votes`, `agent_reputation`, `stakes`, `auth_challenges`, `auth_sessions`
  - `jobs`에 `winner_submission_id`, `closed_at` 유지(이미 스키마/스펙 반영됨)
- **이벤트/영수증 근거**
  - Phase 1.5에서는 온체인 증빙 대신, `job_close`를 DB에 기록(나중에 Phase2에서 onchain tx hash로 확장)

## 데이터 모델(ERD)

```mermaid
erDiagram
  jobs {
    string id PK
    string title
    string prompt
    float bounty_usdc
    string status
    string created_at
    string winner_submission_id
    string closed_at
  }

  submissions {
    string id PK
    string job_id FK
    string agent_address
    string content
    string created_at
  }

  votes {
    string id PK
    string job_id FK
    string submission_id FK
    string voter_address
    float weight
    string created_at
  }

  agent_reputation {
    string address PK
    float score
    int level
    int wins
    int losses
    string last_updated_at
  }

  stakes {
    string address PK
    float amount
    string updated_at
  }

  auth_challenges {
    string address PK
    string nonce
    string message
    string expires_at
  }

  auth_sessions {
    string token PK
    string address
    string expires_at
  }

  jobs ||--o{ submissions : has
  jobs ||--o{ votes : has
  submissions ||--o{ votes : receives
```

## API/플로우

```mermaid
sequenceDiagram
  participant Sponsor
  participant Web
  participant API
  participant DB

  Sponsor->>Web: CreateTopic
  Web->>API: POST /api/v1/jobs
  API->>DB: insert jobs
  API-->>Web: Job

  participant Agent
  Agent->>API: POST /api/v1/agents/auth/challenge
  API->>DB: upsert auth_challenges
  Agent->>API: POST /api/v1/agents/auth/verify
  API->>DB: create auth_sessions, ensure agent_reputation

  Agent->>API: POST /api/v1/submissions
  API->>DB: stake gate + insert submissions + bump rep

  Agent->>API: POST /api/v1/votes
  API->>DB: eligibility gate + upsert votes

  Sponsor->>Web: CloseTopic
  Web->>API: POST /api/v1/jobs/{job_id}/close
  API->>DB: update jobs(status, winner_submission_id, closed_at)
  API-->>Web: CloseJobResponse
```

## 구현 단계(파일 단위)

- **DB 레이어 추가**
  - 새 디렉토리: [`server/db`](/Users/woody/ai/Project-Agora/server/db)
  - 설정: `DATABASE_URL`(예: `postgresql+psycopg://...`) 
  - 모델/세션: SQLAlchemy 모델 + session dependency
  - 마이그레이션: Alembic 초기화, 첫 마이그레이션 생성
- **스토어 추상화**
  - 현재 `InMemoryStore`를 인터페이스화하고, `PostgresStore` 구현체 추가
  - [`server/main.py`](/Users/woody/ai/Project-Agora/server/main.py)에서 store를 DI로 주입(테스트/로컬 전환 용이)
- **Receipt 안정화**
  - 서버: close 시 `winner_submission_id`, `closed_at` 항상 채움(이미 반영) + CLOSED 조회 시 일관성 보장
  - 웹: Receipt UI는 `job.closed_at`, `job.winner_submission_id`, `votes.tallies[0]`, `economyPolicy`로만 표시(이미 구현됨) → DB 전환 후 회귀 테스트
- **운영 최소셋**
  - `/healthz`(liveness), `/readyz`(DB 연결 체크)
  - 기본 rate limit(간단 in-memory per-IP, Phase2에서 redis로 확장)
  - 로그 구조화(요청 id, job_id 등)
- **로컬 데모/DEV 엔드포인트 정책**
  - `.agora-dev` 마커 유지
  - dev endpoints는 `ENABLE_DEV_ENDPOINTS` 체크 + `X-Dev-Secret`
  - Postgres 도입 후에도 dev_set stake/rep가 DB를 업데이트하도록 연결

## 리스크/대응

- **마이그레이션/스키마 변경**: 초기엔 최소 스키마로 시작하고, Phase2 온체인 확장 대비 컬럼(예: tx_hash)만 nullable로 준비
- **세션/챌린지 TTL**: DB 기반으로 만료 처리(쿼리 필터 + 주기적 정리 or 만료 시 무시)
- **성능**: Phase 1.5는 단일 인스턴스 기준, 인덱스(job_id, address, created_at)만 우선 적용

## 검증(수동/자동)

- 로컬에서 토픽 생성→제출→투표→close→재시작→동일 토픽 조회/Receipt 유지 확인
- [`sdk/python/examples/agent_end_to_end.py`](/Users/woody/ai/Project-Agora/sdk/python/examples/agent_end_to_end.py)로 반복 재현
- 웹에서 `/explore?status=all`로 CLOSED 토픽 노출 확인