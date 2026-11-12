let currentStep = 1;
const totalSteps = 6;
let isRealMode = false;
let packagesReady = false;
let currentEnvData = null;
let lastConsoleLog = "";
let lastHealthCheck = null;

document.addEventListener("DOMContentLoaded", () => {
  initEventListeners();
  fetchInitialInspection();
  generateRandomPorts();
  setTimeout(renderRealQRCode, 300);
});

function initEventListeners() {
  document.getElementById("btn-prev").addEventListener("click", () => changeStep(currentStep - 1));
  document.getElementById("btn-next").addEventListener("click", () => changeStep(currentStep + 1));

  // Mode Toggle
  const toggle = document.getElementById("mode-toggle");
  toggle.addEventListener("change", (e) => {
    isRealMode = e.target.checked;
    updateModeUI();
  });

  // Step 2: Random port generators & script download
  document.getElementById("btn-re-random").addEventListener("click", generateRandomPorts);
  document.getElementById("btn-re-random-ssh").addEventListener("click", generateRandomPorts);
  const btnDownloadBat = document.getElementById("btn-download-bat");
  if (btnDownloadBat) {
    btnDownloadBat.addEventListener("click", () => {
      const sshPort = document.getElementById("input-ssh-port").value || "29482";
      window.location.href = `/api/download-windows-script?ssh_port=${sshPort}`;
    });
  }

  // Step 3: Install / Check packages
  document.getElementById("btn-simulate-install").addEventListener("click", executePackageCheckOrInstall);

  // Step 4: Token verify & service create
  document.getElementById("btn-verify-token").addEventListener("click", executeTokenVerify);

  // Step 5: Service deploy
  document.getElementById("btn-deploy-services").addEventListener("click", executeServiceDeploy);

  // Step 6: Generate Keypair
  document.getElementById("btn-generate-key").addEventListener("click", executeGenerateKeypair);

  // Stepper indicator clicks
  document.querySelectorAll(".step-indicator").forEach(el => {
    el.addEventListener("click", () => {
      const targetStep = parseInt(el.getAttribute("data-step"));
      if (targetStep) changeStep(targetStep);
    });
  });

  // Dynamic input sync
  document.getElementById("input-domain").addEventListener("input", () => {
    syncValues();
    renderRealQRCode();
  });
  document.getElementById("input-ssh-port").addEventListener("input", () => {
    syncValues();
    renderRealQRCode();
  });

  // Modal backdrop click to close
  const modal = document.getElementById("agy-help-modal");
  modal.addEventListener("click", (e) => {
    if (e.target === modal) closeAgyHelpModal();
  });
}

function updateModeUI() {
  const modeText = document.getElementById("mode-text");
  const banner = document.getElementById("mode-banner");
  const bannerDesc = document.getElementById("banner-desc");
  const installBtnText = document.getElementById("install-btn-text");

  if (isRealMode) {
    modeText.innerText = "⚡ 실제 설치 모드";
    modeText.style.color = "#fbbf24";
    banner.className = "mode-banner real-mode";
    bannerDesc.innerHTML = "<strong>⚡ 실제 설치 모드:</strong> 버튼 클릭 시 현재 사용자 시스템(<code>~/.config/systemd/user</code>, <code>~/.ssh</code> 등)에 실제 설정이 적용됩니다.";
    installBtnText.innerText = "🔍 실제 패키지 설치 상태 검사 및 반영";
  } else {
    modeText.innerText = "💡 시뮬레이션 모드";
    modeText.style.color = "var(--text-main)";
    banner.className = "mode-banner sim-mode";
    bannerDesc.innerHTML = "<strong>💡 시뮬레이션 모드:</strong> 시스템 설정을 변경하지 않고 각 단계의 구성 흐름을 안전하게 미리 확인합니다.";
    installBtnText.innerText = "🚀 필수 패키지 자동 설치 시작 (시뮬레이션)";
  }
}

function changeStep(newStep) {
  if (newStep < 1 || newStep > 7) return;

  // Package Gate: Enforce package inspection/readiness before accessing Step 4+
  if (newStep > 3 && !packagesReady) {
    alert("⚠️ 필수 패키지(tmux, openssh-server 등)가 준비되지 않았습니다.\n먼저 Step 3에서 [패키지 점검 및 설치]를 완료하세요.");
    return;
  }

  const oldSection = document.getElementById(`step-${currentStep}`);
  if (oldSection) oldSection.classList.remove("active");

  const oldIndicator = document.querySelector(`.step-indicator[data-step="${currentStep}"]`);
  if (oldIndicator) {
    oldIndicator.classList.remove("active");
    if (newStep > currentStep) oldIndicator.classList.add("completed");
  }

  currentStep = newStep;

  const newSection = document.getElementById(`step-${currentStep}`);
  if (newSection) newSection.classList.add("active");

  const newIndicator = document.querySelector(`.step-indicator[data-step="${currentStep}"]`);
  if (newIndicator) {
    newIndicator.classList.add("active");
    newIndicator.classList.remove("completed");
  }

  const btnPrev = document.getElementById("btn-prev");
  const btnNext = document.getElementById("btn-next");
  const counter = document.getElementById("curr-step-num");

  btnPrev.disabled = (currentStep === 1);

  if (currentStep <= totalSteps) {
    counter.innerText = currentStep;
    btnNext.innerText = (currentStep === totalSteps) ? "최종 완료 확인 ▶" : "다음 단계 ▶";
    btnNext.style.display = "inline-block";
  } else {
    counter.innerText = totalSteps;
    btnNext.style.display = "none";
  }

  syncValues();
  if (currentStep === 6) {
    renderRealQRCode();
  }
}

function syncValues() {
  const domain = document.getElementById("input-domain").value || "myagy.example.com";
  const sshPort = document.getElementById("input-ssh-port").value || "29482";

  const cmdElem = document.getElementById("cmd-portproxy");
  if (cmdElem) {
    cmdElem.innerHTML = `<code>netsh interface portproxy add v4tov4 listenport=${sshPort} listenaddress=0.0.0.0 connectport=22 connectaddress=%WSL_IP%</code>`;
  }

  const portElem = document.getElementById("display-port");
  if (portElem) portElem.innerText = sshPort;

  const finalUrl = document.getElementById("final-web-url");
  if (finalUrl) finalUrl.innerText = `https://${domain}`;

  const finalPort = document.getElementById("final-ssh-port");
  if (finalPort) finalPort.innerText = sshPort;
}

async function fetchInitialInspection() {
  try {
    const res = await fetch("/api/inspect");
    const data = await res.json();
    if (data.status === "success") {
      currentEnvData = data;
      document.getElementById("env-os").innerText = data.environment.os;
      document.getElementById("env-user").innerText = data.environment.user;
      document.getElementById("env-home").innerText = data.environment.home;
      document.getElementById("display-user").innerText = data.environment.user;

      data.checks.forEach(c => {
        if (c.name.includes("WSL2")) document.getElementById("inspect-wsl").innerText = c.detail;
        if (c.name.includes("Linux")) document.getElementById("inspect-distro").innerText = c.detail;
        if (c.name.includes("systemd")) document.getElementById("inspect-systemd").innerText = c.detail;
      });

      if (data.installed_packages) {
        updatePackageBadges(data.installed_packages);
      }
    }
  } catch (err) {
    console.error("Inspect fetch error:", err);
  }
}

function updatePackageBadges(pkgs) {
  const map = {
    tmux: "status-tmux",
    ttyd: "status-ttyd",
    openssh: "status-openssh",
    cloudflared: "status-cloudflared"
  };
  for (const [name, id] of Object.entries(map)) {
    const el = document.getElementById(id);
    if (!el) continue;
    if (pkgs[name]) {
      el.innerText = "설치됨 ✔";
      el.className = "pkg-badge ready";
    } else {
      el.innerText = "미설치";
      el.className = "pkg-badge";
      el.style.background = "#ef4444";
      el.style.color = "#fff";
    }
  }
}

async function generateRandomPorts() {
  try {
    const res = await fetch("/api/generate-ports");
    const data = await res.json();
    if (data.status === "success") {
      document.getElementById("input-ttyd-port").value = data.ports.ttyd_port;
      document.getElementById("input-ssh-port").value = data.ports.ssh_port;
      syncValues();
      renderRealQRCode();
    }
  } catch (err) {
    console.error("Port generation error:", err);
  }
}

async function executePackageCheckOrInstall() {
  const btn = document.getElementById("btn-simulate-install");
  const btnText = document.getElementById("install-btn-text");
  const consoleBox = document.getElementById("install-console");
  const consoleOutput = document.getElementById("install-output");

  btn.disabled = true;
  btnText.innerText = "진행 중...";
  consoleBox.style.display = "block";
  consoleOutput.innerText = "";

  try {
    const res = await fetch("/api/install-packages", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ real_mode: isRealMode })
    });
    const data = await res.json();

    if (isRealMode) {
      consoleOutput.innerText = `[Real Mode] 시스템 패키지 검사 결과:\n`;
      data.packages.forEach(p => {
        consoleOutput.innerText += `- ${p.name}: ${p.status} ${p.detail ? '(' + p.detail + ')' : ''}\n`;
      });

      if (data.missing && data.missing.length > 0) {
        packagesReady = false;
        consoleOutput.innerText += `\n[필수 조치 필요]:\n터미널에서 아래 명령을 실행하여 누락된 패키지를 먼저 설치하세요:\n${data.install_command}\n`;
        btnText.innerText = "⚠️ 패키지 설치 필요 (터미널 설치 후 다시 클릭)";
        btn.classList.add("btn-secondary");
      } else {
        packagesReady = true;
        consoleOutput.innerText += `\n✔ 모든 필수 바이너리가 시스템에 완벽히 구비되었습니다.\n`;
        btnText.innerText = "✔ 패키지 점검 완료 (다음 단계로 진행하세요)";
        btn.classList.remove("btn-secondary");
        btn.classList.add("btn-primary");
      }
    } else {
      packagesReady = true;
      const logs = [
        "Reading package lists... Done",
        "Building dependency tree... Done",
        "The following NEW packages will be installed: tmux ttyd openssh-server cloudflared",
        "Setting up tmux (3.4)...",
        "Setting up ttyd (1.7.4 Standalone)...",
        "Setting up cloudflared connector...",
        "Setting up wsl-key-feeder and tm-jump...",
        "All packages installed successfully! (Simulation Mode)"
      ];
      for (let i = 0; i < logs.length; i++) {
        await new Promise(r => setTimeout(r, 120));
        consoleOutput.innerText += logs[i] + "\n";
      }
      btnText.innerText = "✔ 패키지 점검 완료 (다음 단계로 진행하세요)";
    }
    lastConsoleLog = consoleOutput.innerText;
  } catch (err) {
    consoleOutput.innerText = "오류 발생: " + err.message;
    lastConsoleLog = consoleOutput.innerText;
  } finally {
    btn.disabled = false;
  }
}

async function executeTokenVerify() {
  const domain = document.getElementById("input-domain").value;
  const token = document.getElementById("input-token").value;
  const resultElem = document.getElementById("token-test-result");

  resultElem.innerText = "처리 중...";
  resultElem.className = "test-result";

  try {
    const res = await fetch("/api/verify-token", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, domain, real_mode: isRealMode })
    });
    const data = await res.json();

    if (data.status === "success") {
      resultElem.innerText = `✔ ${data.message}`;
      resultElem.className = "test-result success";
    } else {
      resultElem.innerText = `❌ ${data.message}`;
      resultElem.className = "test-result error";
    }
  } catch (err) {
    resultElem.innerText = "통신 오류: " + err.message;
  }
}

async function executeServiceDeploy() {
  const ttydPort = document.getElementById("input-ttyd-port").value;
  const domain = document.getElementById("input-domain").value;
  const deployResult = document.getElementById("deploy-result");

  deployResult.style.display = "block";
  deployResult.innerHTML = "서비스 배포 및 등록 작업 진행 중...";

  try {
    const res = await fetch("/api/deploy-services", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ttyd_port: ttydPort, domain: domain, real_mode: isRealMode })
    });
    const data = await res.json();

    deployResult.className = `deploy-message ${data.status}`;
    deployResult.innerHTML = `
      <strong>${data.status === 'success' ? '✔' : '⚠️'} ${data.message}</strong><br>
      - <code>ttyd.service</code>: [활성화 및 시작됨] (루프백 포트: ${ttydPort})<br>
      - <code>cloudflared.service</code>: [활성화됨] (도메인: ${domain})<br>
      - <code>loginctl enable-linger</code>: [백그라운드 지속 활성화]
    `;

    if (isRealMode) {
      await runLiveHealthCheck(ttydPort);
    } else {
      document.getElementById("badge-ttyd").innerText = "Active ✔";
      document.getElementById("badge-ttyd").style.color = "#10b981";
      document.getElementById("badge-cf").innerText = "Active ✔";
      document.getElementById("badge-cf").style.color = "#10b981";
      document.getElementById("badge-linger").innerText = "Enabled ✔";
      document.getElementById("badge-linger").style.color = "#10b981";
    }
  } catch (err) {
    deployResult.className = "deploy-message error";
    deployResult.innerHTML = "배포 중 오류 발생: " + err.message;
  }
}

async function runLiveHealthCheck(ttydPort) {
  try {
    const res = await fetch(`/api/health-check?ttyd_port=${ttydPort}`);
    const data = await res.json();
    if (data.status === "success") {
      lastHealthCheck = data.health;
      const h = data.health;
      const ttydBadge = document.getElementById("badge-ttyd");
      const cfBadge = document.getElementById("badge-cf");
      const lingerBadge = document.getElementById("badge-linger");

      ttydBadge.innerText = (h.ttyd_service && h.ttyd_port_open) ? "Active (Port OK) ✔" : "Starting...";
      ttydBadge.style.color = (h.ttyd_service && h.ttyd_port_open) ? "#10b981" : "#fbbf24";

      cfBadge.innerText = h.cloudflared_service ? "Active ✔" : "Ready";
      cfBadge.style.color = h.cloudflared_service ? "#10b981" : "#94a3b8";

      lingerBadge.innerText = "Enabled ✔";
      lingerBadge.style.color = "#10b981";
    }
  } catch (e) {
    console.log("Health check fetch error:", e);
  }
}

async function executeGenerateKeypair() {
  const authStatus = document.getElementById("display-auth-status");
  authStatus.innerText = "키페어 생성 중...";

  try {
    const res = await fetch("/api/generate-keypair", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ real_mode: isRealMode })
    });
    const data = await res.json();

    if (data.status === "success") {
      authStatus.innerText = isRealMode
        ? `✔ 키 생성 완료 (~/.ssh/id_keybridge_wizard 등록됨)`
        : `✔ 시뮬레이션 키페어 발급 완료`;
      authStatus.style.color = "#10b981";
      renderRealQRCode();
      alert(data.message || "새 SSH 키페어가 발급되었습니다.");
    }
  } catch (err) {
    authStatus.innerText = "키 생성 오류: " + err.message;
  }
}

function renderRealQRCode() {
  const container = document.getElementById("qr-real-box");
  if (!container || typeof QRCode === "undefined") return;

  container.innerHTML = "";
  const host = "192.168.0.x";
  const port = document.getElementById("input-ssh-port") ? document.getElementById("input-ssh-port").value : "29482";
  const user = currentEnvData?.environment?.user || "wsl_user";
  
  // Format for KeyBridge App pairing
  const payload = JSON.stringify({
    app: "KeyBridge",
    host: host,
    port: parseInt(port),
    user: user,
    auth: "ed25519"
  });

  try {
    new QRCode(container, {
      text: payload,
      width: 140,
      height: 140,
      colorDark: "#0f172a",
      colorLight: "#ffffff",
      correctLevel: QRCode.CorrectLevel.M
    });
  } catch (err) {
    console.error("QR Code generation error:", err);
  }
}

/* ==============================================================================
   AGY CLI One-Click Prompt Generator & Modal Logic
   ============================================================================== */
const stepNames = {
  1: "Step 1: 환경 사전 진단 (Environment Inspection)",
  2: "Step 2: 포트 배정 및 Windows 호스트 연동",
  3: "Step 3: 필수 패키지 점검 및 설치",
  4: "Step 4: 도메인 & Cloudflare Tunnel 연동",
  5: "Step 5: Read-Only Web 터미널 서비스 배포",
  6: "Step 6: 모바일 KeyBridge 앱 페어링"
};

function buildAgyPrompt(step) {
  const stepTitle = stepNames[step] || `Step ${step}`;
  const osInfo = currentEnvData?.environment?.os || "Linux / WSL2";
  const userInfo = currentEnvData?.environment?.user || "$USER";
  const homeInfo = currentEnvData?.environment?.home || "$HOME";
  const modeStr = isRealMode ? "실제 설치 모드 (Real Mode)" : "시뮬레이션 모드 (Simulation Mode)";

  let detailLog = "";
  if (step === 1) {
    detailLog = `[Step 1 진단 상태]\n` +
      `- WSL2 여부: ${document.getElementById("inspect-wsl")?.innerText || "미확인"}\n` +
      `- Linux 배포판: ${document.getElementById("inspect-distro")?.innerText || "미확인"}\n` +
      `- systemd 지원: ${document.getElementById("inspect-systemd")?.innerText || "미확인"}`;
  } else if (step === 2) {
    const ttydPort = document.getElementById("input-ttyd-port")?.value || "34281";
    const sshPort = document.getElementById("input-ssh-port")?.value || "29482";
    detailLog = `[Step 2 포트 및 배치파일]\n` +
      `- ttyd 포트: ${ttydPort}\n` +
      `- SSH 외부 포트: ${sshPort}\n` +
      `- 배치파일(setup-windows-host.bat) 실행 또는 포트포워딩 이슈 발생`;
  } else if (step === 3) {
    detailLog = `[Step 3 패키지 콘솔 로그]\n` + (lastConsoleLog || "패키지 검사 미실행 또는 에러 로그 없음");
  } else if (step === 4) {
    const domain = document.getElementById("input-domain")?.value || "myagy.example.com";
    const tokenStatus = document.getElementById("token-test-result")?.innerText || "토큰 미검증";
    detailLog = `[Step 4 Cloudflare 상태]\n- 도메인: ${domain}\n- 토큰 검증 결과: ${tokenStatus}`;
  } else if (step === 5) {
    const deployText = document.getElementById("deploy-result")?.innerText || "배포 로그 없음";
    detailLog = `[Step 5 배포 및 헬스체크]\n- 결과: ${deployText}\n- 헬스체크: ${JSON.stringify(lastHealthCheck || {})}`;
  } else if (step === 6) {
    const authStatus = document.getElementById("display-auth-status")?.innerText || "미발급";
    detailLog = `[Step 6 모바일 페어링]\n- SSH 인증 상태: ${authStatus}\n- 스마트폰 KeyBridge 연결 실패`;
  }

  return `[WSL2 AGY Setup Wizard 장애 해결 지원 요청]
안녕하세요 AGY, 현재 'wsl-agy-setup-wizard'를 통해 듀얼 디스플레이 개발 환경을 구축하고 있는데, 아래 단계에서 문제가 발생했어.

1. 기본 환경 정보:
- 대상 단계: ${stepTitle}
- OS / 배포판: ${osInfo}
- 사용자 및 경로: ${userInfo} (${homeInfo})
- 마법사 동작 모드: ${modeStr}

2. 현재 단계 상세 상태 및 로그:
\`\`\`
${detailLog}
\`\`\`

3. 요청 사항:
- 본 프로젝트에 포함된 \`TROUBLESHOOTING.md\` 매뉴얼을 직접 참고해서 현재 원인이 무엇인지 진단해줘.
- 문제 해결을 위해 내 WSL2 환경에서 즉시 실행할 수 있는 원자적(Atomic) 복구 명령어 또는 자동 조치를 직접 수행해줘.`;
}

function openAgyHelpModal(step) {
  const prompt = buildAgyPrompt(step);
  document.getElementById("prompt-preview-text").innerText = prompt;
  document.getElementById("agy-help-modal").classList.add("active");
}

function closeAgyHelpModal() {
  document.getElementById("agy-help-modal").classList.remove("active");
}

function copyAgyPrompt() {
  const text = document.getElementById("prompt-preview-text").innerText;
  navigator.clipboard.writeText(text).then(() => {
    closeAgyHelpModal();
    showToast("📋 AGY CLI 문제 해결 프롬프트가 클립보드에 복사되었습니다!");
  }).catch(() => {
    alert("클립보드 복사 실패: 화면의 프롬프트를 직접 드래그하여 복사하세요.");
  });
}

function showToast(msg) {
  const toast = document.getElementById("toast-notice");
  if (!toast) return;
  toast.innerText = msg;
  toast.style.display = "block";
  setTimeout(() => {
    toast.style.display = "none";
  }, 3500);
}

function copySnippet(elementId) {
  const text = document.getElementById(elementId).innerText;
  navigator.clipboard.writeText(text).then(() => {
    showToast("명령어가 클립보드에 복사되었습니다!");
  });
}

function restartWizard() {
  document.querySelectorAll(".step-indicator").forEach(el => {
    el.classList.remove("completed");
  });
  packagesReady = false;
  changeStep(1);
}
