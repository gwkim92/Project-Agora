# Staging Security Notes (인증/쿠키/헤더)

스테이징은 “프로덕션에 준하는 보안 속성”을 먼저 강제하고, 운영 중 발견되는 UX/호환성 이슈를 조정한다.

## 인증(지갑 서명)
- Flow: `challenge` → `personal_sign` → `verify` → bearer token 발급
- 서버는 **TTL이 있는 challenge를 저장**하고, `verify` 성공 시 **challenge를 즉시 소비(삭제)** 하여 재사용(Replay)을 막는다.

## Web(BFF) 쿠키
Next.js BFF는 `HttpOnly` 쿠키로 세션 토큰을 보관한다.

권장:
- `HttpOnly: true`
- `Secure: true` (HTTPS 환경에서만 전송)
- `SameSite: strict` (가능하면 유지; 필요 시 `lax`로 완화)
- `Path: /`
- `Max-Age`: 서버 TTL과 맞추거나 더 짧게(보수적)

스테이징에서 Secure를 강제하려면:
- 배포 플랫폼이 HTTPS 종단이면 **쿠키 Secure를 켜야 함**

## 보안 헤더
최소 권장:
- CSP (개발 모드 예외 유지)
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: no-referrer` 또는 `strict-origin-when-cross-origin`
- `Permissions-Policy` (필요 기능만 허용)

## 관측(요청 ID)
서버는 모든 응답에 `X-Request-Id`를 붙인다.
스테이징에서는:
- 프록시/로드밸런서가 `X-Request-Id`를 전달하면 그대로 사용
- 아니면 서버가 생성(UUID)

