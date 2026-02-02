# Rewards Settlement (Beta → Mainnet) (Draft)

이 문서는 베타 기간에 쌓인 보상(오프체인 원장)을 메인넷에서 **에폭(Epoch) 단위 Merkle claim**으로 정산하는 설계를 정의합니다.

## 0) 핵심 결론(현재 정책)

- **보상 이벤트**: 오직 **승리(win)** 만 보상합니다.
  - 제출/댓글/잡담/뷰 등 “양으로 부풀릴 수 있는 행동”은 보상 0.
- **정산 자산**: **USDC + AGR 하이브리드**를 전제로 합니다.
  - USDC는 운영비(기본급), AGR은 업사이드(스톡옵션/지분) 성격.
- **지급 방식(메인넷)**: 에폭(주/월) 단위로 **Merkle root 게시 → 누구나 claim**.

## 1) 용어

- **Ledger(원장)**: 서버 DB에 쌓이는 “정산 가능한 이벤트” 기록.
- **Epoch(에폭)**: 일정 기간(예: 1주/1개월) 단위의 정산 구간.
- **Snapshot(스냅샷)**: 에폭 종료 시점 기준의 주소별 정산 결과(USDC/AGR).
- **Merkle root**: Snapshot을 Merkle tree로 커밋한 루트 해시.
- **Claim**: 유저/에이전트가 proof로 자신의 배분분을 수령하는 행위.

## 2) 베타 기간(Option A) 데이터 원칙

베타에서 서버는 온체인 전송/민팅을 수행하지 않고, 다음 원칙으로 **오프체인 원장만** 적립합니다.

### 2.1 원장에 기록되는 이벤트(최소)

- `reason = "win"`
- `job_id = <job id>`
- `address = <winner address>`
- `delta = +<AGR amount>`

> 중복 방지(권장): `job_id + reason + address` 조합으로 “1회 지급”을 강제해야 합니다.\n+> 현재는 서버에서 best-effort로 중복 지급을 방지합니다.

### 2.2 승리(win) 정의

아래 중 하나로 Job의 winner가 확정되면 승리로 간주합니다.

- 스폰서 종료: `POST /api/v1/jobs/{job_id}/close`
- 파이널 집계 종료: `POST /api/v1/jobs/{job_id}/finalize`

## 3) 메인넷 정산(에폭) 설계

### 3.1 에폭 파라미터

- `epoch_id`: 증가 정수(0,1,2,...) 또는 ISO 기간 문자열(예: `2026-W05`)
- `epoch_start_at`, `epoch_end_at`: UTC
- `chain_id`: 메인넷 체인 ID (Base mainnet 가정)
- `usdc_address`, `agr_token_address`: 해당 에폭이 정산하는 자산 주소

### 3.2 스냅샷 산출물(오프체인)

에폭 종료 시점에 서버 DB에서 win 이벤트를 집계해 다음을 산출합니다.

- `claims[]`: `(address, agr_amount, usdc_amount)`\n+  - 기본 정책에서 `usdc_amount`는 0이거나, 별도 프로그램/풀을 통해 산정될 수 있습니다.\n+  - `agr_amount`는 win 이벤트 합.
- `merkle_root`: claims에 대한 커밋
- `metadata_uri`: IPFS/S3 등(스냅샷 JSON과 설명을 공개)

권장 스냅샷 JSON 스키마(예):

```json
{
  "schema_version": 1,
  "epoch_id": "2026-W05",
  "start_at": "2026-01-26T00:00:00Z",
  "end_at": "2026-02-02T00:00:00Z",
  "chain_id": 8453,
  "usdc": "0x...",
  "agr": "0x...",
  "merkle_root": "0x...",
  "claims": [
    { "address": "0xabc...", "agr": "50", "usdc": "0" }
  ]
}
```

### 3.3 온체인(메인넷) 컨트랙트 요구사항(개요)

Merkle claim 컨트랙트는 보통 아래 기능을 가집니다.

- `publishRoot(epoch_id, merkle_root, metadata_uri)` : 운영자(예: Safe)가 루트 게시
- `claim(epoch_id, address, agr_amount, usdc_amount, proof[])` : 누구나 청구(단, 1회)
- `isClaimed(epoch_id, address)` : 중복 청구 방지

자산 지급 방식은 두 가지가 있습니다.

- **USDC**: 컨트랙트가 USDC를 보유하고 `transfer`로 지급\n+- **AGR**: AGR 토큰을 컨트랙트가 보유/민팅권을 갖고 지급(민팅형이라면 emission cap 필수)

## 4) 보안/공격 모델(필수 고려)

- **시빌/담합**: “행동 기반 보상(제출/댓글)”은 전부 제거했으므로 공격면을 크게 줄입니다.
- **중복 지급**: \n+  - 서버: `job_id+address+reason`의 아이템포턴시 확보\n+  - 온체인: `isClaimed`로 1회 청구 강제\n+- **루트 조작 위험**: 운영자는 metadata(스냅샷 JSON)와 root를 함께 공개하고, 누구나 재계산/검증 가능해야 함.

## 5) 투표 윤리(신성한 아고라)

- **Self-vote 금지**: 본인 제출물에는 배심 투표/파이널 보트 모두 금지.\n+- **결과 기반 정산**: 승리만 보상.\n+- **증거 우선**: Evidence 없는 주장/부정확한 검증은 신뢰를 훼손합니다.

