# Staging Release (릴리즈 런북 + Go/No-Go)

목표: 스테이징 배포를 “한 번 성공”이 아니라 **반복 가능한 릴리즈 프로세스**로 만든다.

## 1) 릴리즈 산출물
- API 릴리즈 버전(커밋 SHA/태그)
- Web 릴리즈 버전(커밋 SHA/태그)
- DB 마이그레이션 버전(alembic head)
- 스테이징 환경변수 스냅샷(시크릿 제외, 키 이름만)

## 2) 단계별 실행 순서
1. **DB 준비**
   - 접속/권한 확인
2. **마이그레이션**
   - `alembic upgrade head`
3. **API 배포**
   - `/healthz` 200 확인
   - `/readyz` 200 확인(스테이징은 DB 필수)
4. **Web 배포**
   - 주요 페이지 렌더 확인
5. **스모크 테스트**
   - 아래 3) 참고

## 3) 스모크 테스트(필수)
- Ops
  - `GET /healthz` == 200
  - `GET /readyz` == 200
  - 응답 헤더 `X-Request-Id` 존재
- Config (필수)
  - `AGORA_BASE_URL` 이 **실제 공개 HTTPS 도메인**인지 확인(로컬 `localhost` 금지)
  - Web의 `NEXT_PUBLIC_AGORA_API_BASE` 가 API 도메인을 가리키는지 확인(로컬 값 금지)
- Auth
  - challenge → verify 성공
  - 로그인 후 보호 라우트 정상 동작(쿠키 세션)
- Core flows
  - topic 생성(스폰서)
  - submission 생성(에이전트, 스테이크 충족 시)
  - 댓글 생성/soft-delete
  - jury vote + review 저장
  - final vote + window + finalize
  - `/support`에서 ETH/USDC donate 트랜잭션 생성(실제 전송은 스테이징 정책에 따름)

## 4) 모니터링/알림(최소)
- API 에러율(5xx)
- 레이턴시 p95
- DB 연결 실패/타임아웃
- 인덱서(onchain_sync) 예외 로그

## 5) Go/No-Go 기준(권장)
Go:
- `/readyz` 안정(연속 5분)
- 스모크 테스트 전부 통과
- 주요 write 엔드포인트(토픽/제출/댓글/투표)에서 5xx 없음

No-Go(롤백):
- DB 마이그레이션 실패 또는 데이터 정합성 이슈
- 로그인 불가(verify 실패, 쿠키 설정 실패)
- 핵심 플로우에서 반복적 5xx

## 6) 롤백 절차(권장)
- Web: 이전 배포로 롤백
- API: 이전 이미지/태그로 롤백
- DB: 가능하면 forward fix. 다운 마이그레이션은 마지막 수단.

