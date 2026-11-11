# 에이전트 자가 진단 및 문제 해결 가이드 (TROUBLESHOOTING.md)

> [!NOTE]
> 본 문서는 설치 또는 운영 중 장애가 발생했을 때, **해당 환경의 AGY CLI 및 AI 에이전트가 직접 읽고 스스로 원인을 규명(Diagnosis)하고 원자적 복구 명령(Remediation)을 수행할 수 있도록** 설계된 표준 문제 해결 매뉴얼입니다.

---

## 1. 에이전트 1단계: 원클릭 시스템 종합 진단 (One-Shot Diagnostic Suite)

문제가 보고되면 AGY CLI는 추측하지 않고 아래의 통합 진단 명령어를 실행하여 현재 상태를 1회에 수집합니다.

```bash
echo "=== 1. Systemd User Units Status ===" && \
systemctl --user is-active ttyd.service cloudflared.service || true && \
echo "=== 2. Listening Ports (ttyd & ssh) ===" && \
ss -tlpn | grep -E "ttyd|cloudflared|ssh" || true && \
echo "=== 3. Linger Status for User ===" && \
loginctl show-user $USER --property=Linger || true && \
echo "=== 4. Active tmux Sessions ===" && \
tmux list-sessions || true && \
echo "=== 5. Local ttyd HTTP Ping ===" && \
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:{{ TTYD_PORT }} || echo "ttyd unreachable"
```

---

## 2. 장애 유형별 자가 판별 및 복구 절차 (Failure Scenarios)

### 시나리오 1. 브라우저 접속 시 `502 Bad Gateway` 발생

- **원인 1**: `ttyd.service`가 죽어있거나 로컬 포트가 응답하지 않음.
- **원인 2**: Cloudflare Tunnel 설정의 Ingress 서비스 포트와 실제 `ttyd` 리슨 포트가 불일치함.

#### [자가 판별 커맨드]
```bash
# 1. ttyd 프로세스 활성 여부 확인
systemctl --user status ttyd.service --no-pager

# 2. ttyd가 실제 리슨 중인 포트 확인
ss -tlpn | grep ttyd
```

#### [에이전트 자동 복구 커맨드]
```bash
# ttyd 서비스 재시작 및 실시간 로그 확인
systemctl --user restart ttyd.service && sleep 1 && systemctl --user is-active ttyd.service
```

---

### 시나리오 2. 웹 화면 접속 후 `WebSocket Connection Closed (1006)` 발생

- **증상**: ttyd 초기 HTML은 로딩되나 터미널 화면이 뜨지 않고 웹소켓 에러 발생.
- **원인**: ttyd가 연결하려는 대상 tmux 세션이 생성되지 않았거나 세션명이 불일치함.

#### [자가 판별 커맨드]
```bash
# ttyd 유닛에 설정된 tmux attach 타겟 세션명 확인
grep "ExecStart" ~/.config/systemd/user/ttyd.service

# 실제 실행 중인 tmux 세션 목록 대조
tmux list-sessions
```

#### [에이전트 자동 복구 커맨드]
```bash
# 필요한 기본 tmux 세션이 없으면 백그라운드로 즉시 생성
tmux has-session -t main 2>/dev/null || tmux new-session -d -s main

# ttyd 재시작
systemctl --user restart ttyd.service
```

---

### 시나리오 3. WSL 창을 닫으면 웹 접속이 끊어지는 현상

- **원인**: Linux 유저 세션 Linger(백그라운드 지속)가 활성화되지 않아 WSL2 인스턴스가 절전/종료됨.

#### [자가 판별 커맨드]
```bash
loginctl show-user $USER --property=Linger
# 출력 결과가 Linger=no 인 경우 비정상
```

#### [에이전트 자동 복구 커맨드]
```bash
# 영구 Linger 활성화 (1회 실행)
loginctl enable-linger $USER
```

---

### 시나리오 4. 모바일 KeyBridge에서 `Connection Refused` 발생

- **원인 1**: WSL2 내부의 OpenSSH 서버(`sshd`)가 미구동 상태임.
- **원인 2**: Windows 호스트의 PortProxy 포트포워딩 설정이 누락되었거나 Windows 방화벽에 차단됨.

#### [자가 판별 커맨드]
```bash
# WSL 내부 SSH 서버 상태 점검
sudo service ssh status || sudo systemctl status ssh

# Windows 호스트 PortProxy 바인딩 상태 확인 (Windows PowerShell)
netsh interface portproxy show all
```

#### [에이전트 자동 복구 커맨드]
```bash
# WSL 내부 SSH 서버 시작
sudo service ssh start

# Windows PortProxy 재등록 (Windows PowerShell 관리자 권한)
# netsh interface portproxy add v4tov4 listenport={{ SSH_PORT }} listenaddress=0.0.0.0 connectport=22 connectaddress=127.0.0.1
```

---

### 시나리오 5. 모바일 접속 시 `Permission Denied (publickey)` 발생

- **원인**: KeyBridge 앱에 탑재된 Ed25519 개인키에 대응하는 공개키가 WSL의 `~/.ssh/authorized_keys`에 없거나 권한이 잘못됨.

#### [자가 판별 커맨드]
```bash
ls -la ~/.ssh/authorized_keys
# 권한이 600이 아니거나 .ssh 디렉토리가 700이 아닌 경우 SSH 거부 발생
```

#### [에이전트 자동 복구 커맨드]
```bash
# SSH 보안 퍼미션 자동 정상화
chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys
```

---

### 시나리오 6. Cloudflare Tunnel 토큰 오류 또는 Ingress 오류

- **증상**: 도메인 접속 시 `Cloudflare 1033 Error` 또는 연결 불가.
- **원인**: 발급받은 토큰이 잘못되었거나 `cloudflared` 바이너리가 백그라운드에서 크래시됨.

#### [자가 판별 커맨드]
```bash
journalctl --user -u cloudflared.service -n 30 --no-pager
```

#### [에이전트 자동 복구 커맨드]
```bash
# 터널 프로세스 재시작 및 토큰 검증
systemctl --user restart cloudflared.service && sleep 2 && systemctl --user is-active cloudflared.service
```

---

## 3. 에이전트 자가 검증 완료 조건 (Done Checklist)

자가 대처를 수행한 후, 에이전트는 다음 4개 항목이 모두 `PASS`인지 최종 확인합니다:

- [ ] `systemctl --user is-active ttyd.service` ➔ **active**
- [ ] `systemctl --user is-active cloudflared.service` ➔ **active**
- [ ] `loginctl show-user $USER --property=Linger` ➔ **Linger=yes**
- [ ] `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:{{ TTYD_PORT }}` ➔ **200**
