# Phase 2 Onchain Spec (프로덕션 준비 설계)

이 문서는 Project Agora의 Phase 2에서 **온체인 레이어를 “선택적 검증/투명성”**으로 승격하기 위한 설계 문서다.  
오프체인(Postgres)이 제품의 주 상태(source of truth)로 동작하되, 중요한 사건을 온체인으로 **앵커링/정산/슬래싱**하여 검증 가능성을 높인다.

> 가스 정책: 플랫폼은 대납하지 않는다. 온체인 트랜잭션은 참여자가 지갑으로 가스를 지불한다.

## 1) 목표 범위
- **Anchoring**: 오프체인 상태 스냅샷을 온체인에 기록(머클 루트/해시).
- **Staking**: 참여 조건(최소 스테이크)을 온체인 컨트랙트로 실제화.
- **Slashing**: 명시된 위반에 대해 슬래시 이벤트를 온체인으로 남기고(가능하면 자동), 오프체인에서 분쟁/근거/투표와 연결.
- **Treasury**: 기부금(ETH/USDC) inflow/outflow 투명성 + 출금 정책(멀티시그/타임락).

## 2) 현재 구현/스캐폴딩(베이스라인)
- **Stake 관련**
  - (예상) 컨트랙트: `contracts/AgoraStakeVaultV2.sol`
  - 인덱싱(스캐폴딩): `server/onchain_sync.py` (Deposited/Withdrawn/Slashed 이벤트 폴링)
  - 서버 플래그: `AGORA_ONCHAIN_STAKE_ENABLED`, `AGORA_RPC_URL`, `AGORA_STAKE_CONTRACT_ADDRESS`, `AGORA_ONCHAIN_SYNC_ENABLED`
  - DB 앵커 필드: `stakes.*` (stake_tx_hash/chain_id/contract_address/block/log)
- **Treasury(기부)**
  - 컨트랙트: `contracts/AgoraTreasuryVault.sol`
  - UI: `/support` + `DonateWidget` (ETH/USDC)
- **Receipt 앵커 필드(토픽 종료)**
  - DB: `jobs.close_tx_hash/close_chain_id/close_contract_address/close_block_number/close_log_index`

## 3) Anchoring 설계
### 3.1 앵커 대상(스냅샷 범위)
권장 배치 단위:
- **Job 단위**(토픽 종료 시점): 해당 job의 submissions/votes/final_votes/comments 요약을 한 번에 앵커링
- 또는 **시간 배치**(예: 1시간마다): 여러 job을 묶어 한 root로 기록

### 3.2 스냅샷 포맷(권장)
스냅샷은 JSON canonicalization을 전제로 하며, 최소한 다음을 포함:
- schema_version
- job_id
- job_fields(상태, winner, timestamps)
- submissions_digest(각 submission의 id + content_hash + evidence_hash)
- votes_digest(각 vote의 voter + submission_id + weight + review_hash)
- final_votes_digest
- comments_digest(soft-delete 포함)

### 3.3 온체인 앵커 컨트랙트(제안)
이벤트:
- `AnchorPosted(bytes32 root, string uri, uint256 schemaVersion, bytes32 salt)`
  - root: 머클 루트
  - uri: IPFS CID 또는 서버 URL(스냅샷 본문 위치)
  - salt: 프라이버시/스팸 방지(선택)

### 3.4 DB 저장 필드(추가 제안)
- `anchor_batches` 테이블(또는 jobs에 anchor 메타 추가)
  - anchor_root, anchor_uri
  - anchor_tx_hash, anchor_chain_id, anchor_contract_address, anchor_block_number, anchor_log_index

## 4) Staking 설계
### 4.1 권한/요건
- 최소 스테이크 충족 시:
  - submission 가능
  - vote 가능(추가로 rep 요건)

### 4.2 인덱싱/동기화
`server/onchain_sync.py`는 다음을 보장해야 함:
- 이벤트 폴링 커서 유지(이미 `OnchainCursorDB` 사용)
- idempotent 처리(슬래시 이벤트 id = `chain:tx:logIndex`)
- 장애 시 재시도/중복 삽입 안전

### 4.3 운영 모드
- 스테이징: 폴링 기반 인덱서 단일 인스턴스
- 프로덕션: 인덱서 분리 프로세스(독립 deploy) + 재처리(runbook)

## 5) Slashing 설계
### 5.1 위반 정의(초기)
- 스팸/시빌(대량 댓글/제출)
- 근거 조작(명백한 fabricated evidence)
- 반복적 악의적 투표

### 5.2 집행 모델(단계)
- Phase 2a: 운영자/배심원 합의 → 온체인 슬래시 트랜잭션 실행(멀티시그 권장)
- Phase 2b: 규칙 기반 자동화(증거/투표 결과 기반) — 보안/오탐 리스크 때문에 후순위

### 5.3 오프체인 연결
- 슬래시 이벤트는 job/submission/comment/vote.review와 연결되어야 함(근거 링크)

## 6) Treasury(기부) 출금 정책
- 소유자: Safe(멀티시그) 권장
- 출금 투명성:
  - Outflow 이벤트 기록
  - 목적(purpose bucket) 메모 해시 기록
- 타임락(권장): 큰 금액/민감 액션에만 적용(운영 민첩성 vs 신뢰성 트레이드오프)

## 7) 전환(마이그레이션) 절차
1. 스테이징에서 컨트랙트 배포(테스트넷/스테이징 체인)
2. 서버 설정:
   - `AGORA_ONCHAIN_STAKE_ENABLED=1`, `AGORA_ONCHAIN_SYNC_ENABLED=1`, RPC/주소 설정
3. 인덱서 동기화(lookback 포함)로 stake 상태 재구성
4. Anchoring 컨트랙트 도입 후: 토픽 종료 시 root 생성→게시→DB에 앵커 필드 저장
5. 프로덕션 승격 전 점검:
   - reorg 대응 전략(확정 블록 수)
   - 키관리(멀티시그/권한)
   - 장애 시 재처리(runbook)

