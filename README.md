# WSL2 AGY Dual-Display System Setup Wizard

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Zero Dependency](https://img.shields.io/badge/Dependencies-Zero%20(Pure%20Python%203)-brightgreen.svg)]()
[![Privacy Protected](https://img.shields.io/badge/Privacy-100%25%20Anonymized-success.svg)]()

> **WSL2 + tmux + AGY + Read-Only Web + Android KeyBridge**  
> 누구나 클릭만으로 자신만의 AI 에이전트 듀얼 디스플레이 개발 환경을 구축할 수 있도록 지원하는 대화형 웹 설치 마법사(Setup Wizard) 및 시뮬레이터입니다.

---

## 🌟 시스템 개요 (System Architecture)

본 시스템은 PC(WSL2)의 고성능 터미널 환경과 스마트폰(Android)을 물리 블루투스 키보드로 직결하고, 태블릿이나 보조 화면으로는 Cloudflare Zero Trust 기반의 안전한 웹 터미널을 실시간 미러링하여 **완벽한 이동형 듀얼 디스플레이 워크스페이스**를 제공합니다.

```mermaid
flowchart TD
    subgraph MobileDevice["모바일 (스마트폰 / 태블릿)"]
        PhysKB["물리 블루투스 키보드"] -->|하드웨어 입력| KeyBridge["Donagy KeyBridge 앱\n(0.1ms 무지연 브릿지)"]
        Browser["웹 브라우저 (Chrome/Safari)"] -->|실시간 화면 관제| WebScreen["Read-Only 대시보드"]
    end

    subgraph Cloudflare["Cloudflare Edge Network"]
        Tunnel["Cloudflare Zero Trust Tunnel\n(포트 개방 / IP 노출 없음)"]
    end

    subgraph HostPC["Windows Host PC"]
        PortProxy["Windows PortProxy\n(20000~60000 난수 포트)"]
    end

    subgraph WSL2["WSL2 (Ubuntu Linux)"]
        SSH["OpenSSH Server\n(Ed25519 인증)"]
        Tmux["tmux 멀티플렉서\n(agy cli 상시 가동)"]
        TTYD["ttyd 데몬\n(Read-Only 웹소켓 중계)"]
        Systemd["systemd (User)\n(loginctl linger 상시 유지)"]
    end

    KeyBridge -->|SSH 연결 (난수 포트)| PortProxy -->|로컬 중계| SSH --> Tmux
    WebScreen -->|HTTPS 접속| Tunnel --> TTYD -->|세션 미러링| Tmux
```

---

## 🚀 빠른 시작 (Web GUI 시뮬레이터 체험)

외부 라이브러리 설치 없이 Python 3만 설치되어 있다면 단 1줄로 마법사 시뮬레이터를 즉시 실행할 수 있습니다.

```bash
# 1. 저장소 복제 및 디렉토리 이동
git clone https://github.com/your-org/wsl-agy-setup-wizard.git
cd wsl-agy-setup-wizard

# 2. 웹 설치 마법사 구동 (시뮬레이션 모드)
python3 server.py
```

브라우저에서 **`http://localhost:8080`**에 접속하면 1단계부터 6단계까지의 설치 워크플로우를 직접 클릭하며 체험할 수 있습니다.

---

## 📋 6단계 설치 가이드 워크플로우

1. **Step 1: 환경 자동 진단 (System Inspection)**
   - Windows WSL2 활성화, Linux 배포판, `systemd` 구동 상태, 사용자 계정명을 자동 감지합니다.
2. **Step 2: 네트워크 및 난수 포트 배정 (Port Allocation)**
   - 개인 환경 노출을 방지하기 위해 `20000~60000` 대역 중 미사용 중인 임의의 포트 2개를 자동 추첨합니다.
   - Windows 호스트 `netsh portproxy` 설정 명령어를 자동 생성합니다.
3. **Step 3: 필수 패키지 설치 (Package Provisioning)**
   - `tmux`, `ttyd`, `nginx`, `cloudflared` 바이너리를 원클릭으로 설치합니다.
4. **Step 4: 도메인 & Cloudflare Tunnel 연동 (Zero Trust)**
   - 무료 Cloudflare Tunnel 토큰을 연동하여 공유기 설정이나 공인 IP 노출 없이 HTTPS 도메인을 연결합니다.
5. **Step 5: Read-Only Web 터미널 배포 (Service Activation)**
   - 브라우저에서는 오직 조회만 가능한 `-R (Read-Only)` 안전 모드로 ttyd 및 터널 백그라운드 서비스를 자동 등록합니다.
   - `loginctl enable-linger`를 적용하여 WSL 창을 닫아도 프로세스가 영구 지속됩니다.
6. **Step 6: 모바일 KeyBridge 페어링 (Mobile Setup)**
   - 로컬에서 일회용 Ed25519 SSH 키페어를 생성하고 화면상 QR 코드 또는 원클릭 복사 형태로 모바일 앱에 페어링합니다.

---

## 🔒 개인정보 및 보안 철칙 (Security Principles)

- **100% 익명화 및 템플릿화**: 저장소 코드에는 개인 계정명, 사설 IP, 실제 사용 포트, 도메인, 인증 토큰이 일체 하드코딩되어 있지 않습니다.
- **난수 포트 자동 배정**: 고정 포트 대신 시스템의 미사용 난수 포트를 자동 감지하여 배정하므로 환경 지문이 남지 않습니다.
- **로컬 렌더링**: 모든 개인 설정 파일은 사용자의 로컬 머신 내부에서만 렌더링되며 외부 서버로 전송되지 않습니다.

---

## 📚 관련 상세 문서

- [시스템 아키텍처 상세 명세 (SYSTEM_SPEC.md)](./SYSTEM_SPEC.md) - 전체 컴포넌트, 프로세스 트리, 통신 프로토콜 명세
- [에이전트 자가 진단 및 문제 해결 가이드 (TROUBLESHOOTING.md)](./TROUBLESHOOTING.md) - AGY CLI가 직접 읽고 스스로 문제를 판별/복구할 수 있는 자가 진단 매뉴얼
