# 시스템 아키텍처 상세 명세서 (SYSTEM_SPEC.md)

본 문서는 **WSL2 AGY Dual-Display System**의 기술 구성 요소, 프로세스 라이프사이클, 통신 프로토콜 및 파일 배치 규격을 정의한 상세 명세서입니다.

---

## 1. 컴포넌트 구성 매트릭스 (Components Matrix)

| 컴포넌트 | 패키지/프로세스 | 동작 모드 / 주요 파라미터 | 역할 및 책임 |
| :--- | :--- | :--- | :--- |
| **WSL2** | `Ubuntu 22.04 / 24.04` | Hyper-V 가상화 컨테이너 | 고성능 리눅스 개발 환경 및 AI 코딩 CLI 구동 |
| **systemd (User)** | `systemd --user` | `loginctl enable-linger $USER` | WSL 세션 종료 후에도 서비스 백그라운드 영구 지속 |
| **tmux** | `tmux v3.4+` | 백그라운드 세션 (`agy`, `dev`, `main` 등) | 터미널 다중화, 세션 유지, 물리 키보드 입력 수신 |
| **ttyd** | `ttyd v1.7+` | `-p {{ TTYD_PORT }} -R tmux attach -t ...` | **-R (Read-Only)** 플래그 적용, 브라우저 화면 조회 전용 버퍼 |
| **cloudflared** | Cloudflare Connector | `tunnel run --token {{ CF_TUNNEL_TOKEN }}` | 포트 개방 없이 HTTPS 인그레스를 로컬 `{{ TTYD_PORT }}`로 중계 |
| **Windows PortProxy** | `netsh interface portproxy` | `listenport={{ SSH_PORT }} connectport=22` | 호스트 외부(스마트폰) SSH 패킷을 WSL2 로컬로 중계 |
| **KeyBridge (Android)** | Kotlin 네이티브 앱 | Ed25519 인증, 무지연 터치/키 이벤트 가로채기 | 물리 블루투스 키보드 신호를 WSL tmux로 직결 |

---

## 2. 데이터 흐름 및 네트워크 토폴로지

```
[사용자 입력 경로]
물리 키보드 
   ➔ Android KeyBridge (블루투스 감지)
   ➔ Wi-Fi / VPN (포트 {{ SSH_PORT }})
   ➔ Windows PortProxy (listenport={{ SSH_PORT }})
   ➔ WSL2 OpenSSH (포트 22)
   ➔ tmux 세션 직결 (tmux send-keys / attach)
   ➔ AGY CLI (명령 수신 및 코드 실행)

[화면 관제 출력 경로]
AGY CLI 출력
   ➔ tmux 가상 버퍼 
   ➔ ttyd (-R Read-Only 소켓 브로드캐스트)
   ➔ 로컬 포트 (127.0.0.1:{{ TTYD_PORT }})
   ➔ cloudflared 터널 아웃바운드
   ➔ Cloudflare Zero Trust Edge
   ➔ 모바일/태블릿 브라우저 (HTTPS://{{ USER_DOMAIN }})
```

---

## 3. 프로세스 라이프사이클 및 자동 기동 규격

### 3.1 systemd User Session Linger
WSL2는 기본적으로 터미널 창을 모두 닫으면 배포판이 정지(Stopped) 상태로 전환됩니다. 이를 방지하고 24시간 상시 가동을 보장하기 위해 다음 메커니즘을 준수합니다.

```bash
# 사용자가 로그아웃하거나 WSL 창을 닫아도 사용자 systemd 데몬 유지
loginctl enable-linger $USER
```

### 3.2 서비스 유닛 배치 규격
- **ttyd 서비스 유닛**: `~/.config/systemd/user/ttyd.service`
  - `Restart=always` 및 `RestartSec=3` 설정
  - 바인딩 주소: `127.0.0.1` (외부 직접 노출 원천 차단)
- **Cloudflare 터널 서비스 유닛**: `~/.config/systemd/user/cloudflared.service`
  - `Restart=on-failure`
  - 실행 커맨드: `cloudflared tunnel run --token {{ CF_TUNNEL_TOKEN }}`

---

## 4. 보안 및 권한 격리 (Security Boundary)

1. **Read-Only 가드 (Zero-Tampering)**:
   - 웹 브라우저 화면(`ttyd`)은 반드시 `-R` 옵션으로 실행되어, 브라우저 화면을 통한 임의의 키 입력, 마우스 클릭 또는 원격 조작이 기술적으로 원천 차단됩니다.
2. **비밀번호 없는 공개키(Ed25519) 인증**:
   - 모바일 KeyBridge는 비밀번호 인증을 일체 허용하지 않으며, 전용 Ed25519 개인키로만 SSH 인증을 수행합니다.
3. **로컬 루프백 격리**:
   - `ttyd` 및 서비스 포트는 `0.0.0.0`이 아닌 `127.0.0.1`에만 바인딩되며, 외부 유입은 오직 Cloudflare 암호화 터널 및 인증된 SSH 포트포워딩으로만 가능합니다.
