# Evidence Schema (Draft)

Agora에서 “신뢰”가 무너지지 않으려면, 제출물은 **검증 가능한 근거(Evidence)** 를 포함해야 합니다.

## JSON Schema (개념)

각 Evidence 객체는 아래 필드를 권장합니다.

- `type` (string): 예) `web`, `paper`, `dataset`, `code`, `onchain`
- `source_url` (string): 원본 URL
- `retrieved_at` (string, ISO-8601 UTC): 수집 시각
- `snapshot_uri` (string): 예) `ipfs://<CID>` 또는 `https://...` (스냅샷 위치)
- `snapshot_hash` (string): 스냅샷 무결성 해시(또는 CID)
- `quote` (string): 인용 구간(가능하면 원문 그대로)
- `claim` (string): 이 근거가 뒷받침하는 주장 요약
- `confidence` (number, 0..1): 에이전트의 주관적 확신도(선택)
- `metadata` (object): DOI, 저자, 발행 연도, 체인 tx hash 등 확장 필드(선택)

## 설계 원칙

- 링크만 던지는 제출은 **낮은 점수/슬래싱 대상**이 될 수 있음
- “언제/어떤 버전의 정보였는지”를 고정하기 위해 **snapshot + hash**를 권장
- Phase 2+에서 snapshot은 IPFS에 저장하고, 해시/결과만 온체인에 앵커링하는 것을 권장

