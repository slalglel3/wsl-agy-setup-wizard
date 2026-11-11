# AGENTS.md - WSL AGY Setup Wizard Agent Guidelines

본 가이드라인은 AGY CLI 및 AI 에이전트가 이 프로젝트를 수정, 확장 또는 사용자 환경에서 실행할 때 준수해야 하는 규칙입니다.

## 1. Zero-Credential & Absolute Privacy Rule
- 어떠한 경우에도 실제 사용자의 고유 계정명, 실제 도메인, 고유 비표준 포트, 실제 Cloudflare 토큰, 실제 SSH 개인키를 본 저장소의 코드, 문서, 커밋에 포함하지 않는다.
- 모든 포트는 `20000~60000` 대역의 난수 추천(`{{ TTYD_PORT }}`, `{{ SSH_PORT }}`) 방식을 유지한다.

## 2. Zero-Dependency Pure Python Rule
- 설치 가이드 서버(`server.py`)는 외부 패키지 설치(`pip install`)가 필요 없는 순수 Python 3 표준 라이브러리(`http.server`, `urllib`, `json`, `socket`)만을 사용한다.
- 사용자의 환경 오염을 방지하고 어떤 저사양 리눅스/WSL 환경에서도 즉시 구동될 수 있어야 한다.

## 3. Self-Diagnostics Protocol
- 환경 설정이나 서비스 기동에 문제가 발생했을 때 에이전트는 [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)에 기술된 원클릭 진단 커맨드를 실행하여 원인을 정확히 규명한 후 1:1 복구 커맨드를 수행한다.
