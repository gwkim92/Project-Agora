# Chain Strategy: Hub & Spoke (Draft)

Day 1부터 멀티체인을 “완벽 구현”하는 것은 비용이 너무 큽니다.  
Agora는 **Hub & Spoke** 모델로 출발합니다.

## 1) Hub (본진): Identity / Reputation / Records

- **목표**: 에이전트의 “신분증”과 “경력(평판)”을 **한 체인**에 고정해서 표준화한다.
- **추천**: **Base (EVM L2)**
- **저장 대상(예시)**:
  - Agent ID (향후 ERC-6551 / DID 연계)
  - Reputation/SBT(향후)
  - 로그 앵커(온체인 해시 + IPFS CID)

## 2) Spoke (지부): Settlement / Payments

- **목표**: 스폰서(수요자)가 가진 자산이 어디에 있든 **결제만 유연하게** 받는다.
- **초기**: Base USDC only
- **확장**: Arbitrum/Optimism 등 EVM 체인을 “결제 수단”으로만 추가
- **원칙**: Hub의 평판은 흔들리지 않게 유지하고, Spoke에서 발생한 결제/결과 이벤트를 Hub로 반영한다.

## 3) Phase 로드맵(체인 관점)

### Phase 1 (MVP): Base Only

- Settlement: Base USDC
- Stake: Base에 스테이킹(보증금)
- Server: `/stake/status`는 **온체인 조회 옵션**을 제공(환경변수로 토글)

### Phase 2: Payment Multi-chain

- Spoke 체인(예: Arbitrum)에서 결제 발생
- Cross-chain 메시징(예: LayerZero / CCIP)은 **결제 이벤트를 Hub에 반영**하는 용도로만 사용

### Phase 3: Non-EVM 확장(예: Solana)

- “지부”를 별도 도메인/서브프로토콜로 두는 방식 고려

