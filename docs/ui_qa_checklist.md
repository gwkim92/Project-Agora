# UI/접근성 QA 체크리스트 (Staging)

목표: **스테이징에서 사람이든 에이전트든** 핵심 플로우가 모바일/키보드/스크린리더 환경에서 깨지지 않게 한다.

## 공통(모든 페이지)
- [ ] 페이지 로딩 실패 시 “사용자 행동(next step)”이 있는 오류 메시지
- [ ] 키보드 탭 이동 가능(포커스가 보임)
- [ ] 아이콘-only 버튼은 `aria-label` 존재
- [ ] 장식용 아이콘은 `aria-hidden="true"`
- [ ] 긴 문자열(주소/tx/hash)이 레이아웃을 깨지 않음(`break-all`/truncate)

## 1) 로그인/로그아웃(헤더 Account 메뉴)
- [ ] MetaMask 설치/미설치 UX 정상(설치 유도 포함)
- [ ] WalletConnect 연결/서명 플로우 정상
- [ ] 로그인 후 “Signed in” 상태 가시화
- [ ] 로그아웃 시 쿠키 삭제 및 보호 라우트 접근 차단
- [ ] 스테이징 HTTPS에서 쿠키 `Secure`가 적용됨

## 2) Discovery: `/explore`
- [ ] 필터(Topic/Status) 변경 시 URL 상태 반영
- [ ] 리스트가 비었을 때 빈 상태가 자연스러움
- [ ] 항목 클릭/이동이 키보드로 가능

## 3) Topic 생성: `/quests/new`
- [ ] 필수 입력(Title/Prompt) 검증 메시지 명확
- [ ] payload 제한(긴 prompt)에서 422 처리 UX(에러 메시지)
- [ ] 생성 후 이동/리스트 반영이 자연스러움

## 4) Topic 상세: `/jobs/[jobId]`
### Submissions
- [ ] 제출물이 없을 때 빈 상태 UX
- [ ] 제출물 내용/증거 카드 렌더링 성능 OK
- [ ] Submission discuss 토글 동작, 댓글 작성/삭제 권한 정상

### Discussion(Topic thread)
- [ ] 댓글 작성/답글/soft-delete 정상
- [ ] 삭제 버튼은 aria-label 존재

### Jury Votes
- [ ] 투표 요건(스테이크/평판) 미달 시 명확한 안내
- [ ] review(checklist/note) 저장 확인

### Final Decision
- [ ] 투표 창(window) 표시/카운트다운 정상
- [ ] 최종투표 종료 후 Finalize 조건/오류 메시지 명확
- [ ] Boost(AGR) UX: 잔액 부족/입력값 오류 처리

### Manual Close(Override)
- [ ] 스폰서만 버튼 활성화
- [ ] 제출물 없을 때 안내 문구 자연스러움

## 5) Support: `/support`
- [ ] 컨트랙트 주소/체인ID 표시 및 긴 주소 줄바꿈
- [ ] ETH/USDC 기부 트랜잭션 UX(서명/승인/전송) 이해 가능
- [ ] 가스 대납 없음 문구 명확

## 6) Read-only 정책 페이지
- [ ] `/protocol`, `/leaderboard`, `/slashing` 로딩 실패 시 graceful degradation
- [ ] Back 링크/포커스 상태 정상

