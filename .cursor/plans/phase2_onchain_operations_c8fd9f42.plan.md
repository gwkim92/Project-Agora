---
name: Phase2 Onchain Operations
overview: 운영자 Safe가 실행하는 모델로 온체인 싱크(인덱서)·앵커링·슬래싱·기부 감지 기반 donor 아바타를 프로덕션 운영 가능한 수준으로 설계합니다.
todos:
  - id: phase2-indexer-prodize
    content: onchain_sync를 독립 프로세스/확정블록/메트릭/재처리 가능한 형태로 설계(커서·idempotency·reorg 대응)
    status: pending
  - id: phase2-anchoring-design
    content: job 종료 시 스냅샷 생성→root/uri 산출→Safe가 Anchor 컨트랙트에 게시→receipt 저장까지 전체 설계(테이블/필드 포함)
    status: pending
    dependencies:
      - phase2-indexer-prodize
  - id: phase2-slashing-design
    content: 슬래싱 제안/근거/승인(오프체인)→Safe 집행→온체인 이벤트 인덱싱→DB 연결 설계
    status: pending
    dependencies:
      - phase2-indexer-prodize
  - id: phase2-donor-avatar-design
    content: Treasury DonationReceived 인덱싱→누적 $10 판정→agent_profiles.avatar_mode=donor 전환→결정적 자동 아바타 생성 규칙 설계(ETH 환산 포함)
    status: pending
    dependencies:
      - phase2-indexer-prodize
  - id: phase2-admin-ops-runbook
    content: "운영 문서: 배포 토폴로지(VM), 모니터링 지표, 커서 리셋/백필 절차, 키관리(Safe) 체크리스트 작성"
    status: pending
    dependencies:
      - phase2-anchoring-design
      - phase2-slashing-design
      - phase2-donor-avatar-design
isProject: false
---

# Phase 2 온체인 운영 설계(인덱서·앵커링·슬래싱·Donor 아바타)

## 목표/원칙

- **오프체인(DB)이 Source of Truth**이며, 온체인은 **검증/투명성/경제적 집행** 레이어로 사용.
- **가스 대납 없음**: 트랜잭션 실행 주체는 **운영자 Safe(멀티시그)**. [[memory:13504885]]
- 앵커링은 **job 종료 시점마다 1회** 실행.
- Donor 아바타는 **누적 $10 이상 기부** 시 자동 부여.

## 현상태(베이스라인) 요약

- 스테이크 이벤트 폴링 스캐폴드 존재: `[server/onchain_sync.py](/Users/woody/ai/Project-Agora/server/onchain_sync.py)`
  - 현재는 StakeVault `Deposited/Withdrawn/Slashed` 이벤트만 추적, 커서는 `OnchainCursorDB`에 저장.
- Treasury 컨트랙트 이벤트 정의 존재: `[contracts/AgoraTreasuryVault.sol](/Users/woody/ai/Project-Agora/contracts/AgoraTreasuryVault.sol)`
  - `DonationReceived(donor, asset, amount, purposeId, memoHash)`, `TreasurySpent(...)`
- Phase2 설계 문서 초안 존재: `[docs/phase2_onchain_spec.md](/Users/woody/ai/Project-Agora/docs/phase2_onchain_spec.md)`

## 아키텍처(프로덕션 기준)

### 1) Onchain Sync(인덱서) 상시 운영 모델

- **인덱서는 API 프로세스와 분리된 독립 프로세스**로 운영.
  - (이유) API 재시작/스케일아웃과 동기화 작업을 분리해서 안정성 확보.
- 동작 단위는 `sync_once()`의 확장판:
  - (a) StakeVault 이벤트 폴링(기존)
  - (b) TreasuryVault 이벤트 폴링(신규)
  - (c) (추후) Anchor 컨트랙트 이벤트 폴링(신규)
- 핵심 운영 요소
  - **Cursor**: 컨트랙트/체인별 `next_from_block`을 DB에 저장(이미 패턴 있음)
  - **Idempotency**: 이벤트 id를 `chain:tx:logIndex`로 고정(이미 SlashingEvent가 사용)
  - **Reorg 안전성**: 확정 블록 수 `CONFIRMATIONS` 도입(예: 20~50)
    - `to_block = latest - CONFIRMATIONS`로 처리해 롤백 위험 완화
  - **재처리(runbook)**: cursor를 특정 블록으로 되돌려 재동기화 가능
  - **관측성**: 마지막 성공 시각, 처리 블록 범위, 이벤트 처리량, 에러 카운트 메트릭 제공

### 2) Anchoring(오프체인 스냅샷 루트) — job 종료 시점 1회

- 트리거: `POST /api/v1/jobs/{job_id}/close` 후
  - 운영자 Safe가 **별도 트랜잭션**으로 Anchor 컨트랙트에 `AnchorPosted(root, uri, schemaVersion, salt)`를 실행
- 데이터 흐름
  - 서버는 job 종료 시점에 **canonical snapshot JSON** 생성 → `root`(머클 또는 해시) 산출 → `uri`(IPFS/HTTP) 저장
  - Safe가 온체인 게시 후, 서버는 **anchor receipt(tx_hash, chain_id, contract, block, logIndex)**를 DB에 기록
- DB 설계
  - 옵션 A(추천): `anchor_batches` 테이블 신설(여러 job 확장 대비)
  - 옵션 B: `jobs`에 anchor 필드 추가(단순)
  - 최소 필드: `job_id, anchor_root, anchor_uri, anchor_tx_hash, anchor_chain_id, anchor_contract_address, anchor_block_number, anchor_log_index, schema_version`

### 3) Slashing(온체인 집행) — 자동화는 후순위

- 원칙: **오프체인에서 판정(근거+투표)** → Safe가 `StakeVault.slash(agent, amount, recipient)` 실행
- 서버 책임
  - 슬래시 “제안/근거 링크/승인 상태”를 저장하고(오프체인), 집행 결과를 온체인 receipt로 연결
- 자동 슬래시(Phase 2b)는 나중
  - 오탐/공격면 증가 때문에, 우선은 **human-in-the-loop**로 설계

### 4) “기부 감지 → donor 아바타 자동 생성”

- 트리거: TreasuryVault `DonationReceived` 이벤트 인덱싱
- 정책
  - 누적 기부액이 **$10 이상**이면 `avatar_mode=donor`로 전환
  - USDC: 6 decimals 그대로 합산
  - ETH: 인덱서에서 **가격 오라클(예: Chainlink) 또는 서버 설정 고정 환율** 중 택1(초기에는 고정 환율/수동 보정 추천)
- 프로필 반영
  - 기존 프로필 테이블(이미 추가됨): `agent_profiles.avatar_mode`
  - donor 모드일 때는 `avatar_url`을 비워도 UI가 자동 생성 아바타를 표시(결정적 생성: `address + firstDonationEventId` 기반)

## 보안/운영 고려사항

- **키관리**: Anchor/Slash 실행은 Safe 멀티시그만
- **권한/감사**: 관리자 작업은 `AGORA_OPERATOR_ADDRESSES`로 접근 통제(이미 패턴 존재)
- **재난복구**: cursor 리셋, 백필 범위 확장(lookback), 인덱서 단독 재시작 절차

## Mermaid: 데이터 흐름(요약)

```mermaid
flowchart TD
  User[UserWallet] -->|Donate| TreasuryVault
  TreasuryVault -->|DonationReceived| OnchainLogs
  OnchainLogs --> Indexer
  Indexer -->|UpdateDonationTotals| DB
  DB --> WebUI

  SponsorOrOp[OperatorSafe] -->|CloseJob(offchain)| API
  API --> DB2[(DBSnapshot)]
  OperatorSafe -->|PostAnchorTx| AnchorContract
  AnchorContract -->|AnchorPosted| OnchainLogs2
  OnchainLogs2 --> Indexer2
  Indexer2 -->|SaveAnchorReceipt| DB

  OperatorSafe -->|SlashTx| StakeVault
  StakeVault -->|Slashed| OnchainLogs3
  OnchainLogs3 --> Indexer3
  Indexer3 -->|RecordSlashingEvent| DB
```



## 변경/추가 대상 파일(구현 시)

- 인덱서 확장: `[server/onchain_sync.py](/Users/woody/ai/Project-Agora/server/onchain_sync.py)`
- Treasury ABI/이벤트 인덱싱: `[contracts/AgoraTreasuryVault.sol](/Users/woody/ai/Project-Agora/contracts/AgoraTreasuryVault.sol)`
- Anchor 컨트랙트(신규): `contracts/AgoraAnchorRegistry.sol`(제안)
- DB 마이그레이션(신규): `server/alembic/versions/*_anchor_batches.py`, `*_donations_ledger.py`
- 저장소/모델: `[server/db/models.py](/Users/woody/ai/Project-Agora/server/db/models.py)`, `[server/storage.py](/Users/woody/ai/Project-Agora/server/storage.py)`
- 운영자 UI/관측: `/admin` 확장(메트릭/커서/최근 이벤트)

## 구현 TODO

- 범위는 2단계로 나눔: Phase 2a(운영자 수동 집행) → Phase 2b(부분 자동화)

