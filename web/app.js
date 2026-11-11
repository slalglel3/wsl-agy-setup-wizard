let currentStep = 1;
const totalSteps = 6;
let isRealMode = false;

document.addEventListener("DOMContentLoaded", () => {
  initEventListeners();
  fetchInitialInspection();
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
  document.getElementById("input-domain").addEventListener("input", syncValues);
  document.getElementById("input-ssh-port").addEventListener("input", syncValues);
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
}

function syncValues() {
  const domain = document.getElementById("input-domain").value || "myagy.example.com";
  const sshPort = document.getElementById("input-ssh-port").value || "29482";

  const cmdElem = document.getElementById("cmd-portproxy");
  if (cmdElem) {
    cmdElem.innerHTML = `<code>netsh interface portproxy add v4tov4 listenport=${sshPort} listenaddress=0.0.0.0 connectport=22 connectaddress=127.0.0.1</code>`;
  }

  const hostElem = document.getElementById("display-host");
  if (hostElem) hostElem.innerText = domain;

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
      document.getElementById("env-os").innerText = data.environment.os;
      document.getElementById("env-distro").innerText = data.environment.distribution;
      document.getElementById("env-user").innerText = data.environment.user;
      document.getElementById("env-home").innerText = data.environment.home;
      document.getElementById("display-user").innerText = data.environment.user;

      // Update check details
      data.checks.forEach(c => {
        if (c.name.includes("WSL2")) document.getElementById("inspect-wsl").innerText = c.detail;
        if (c.name.includes("Linux")) document.getElementById("inspect-distro").innerText = c.detail;
        if (c.name.includes("systemd")) document.getElementById("inspect-systemd").innerText = c.detail;
      });

      // Update package badges if available
      if (data.installed_packages) {
        updatePackageBadges(data.installed_packages);
      }
    }
  } catch (err) {
    console.log("Inspection demo fallback");
  }
}

function updatePackageBadges(pkgs) {
  const map = {
    tmux: "status-tmux",
    ttyd: "status-ttyd",
    nginx: "status-nginx",
    cloudflared: "status-cloudflared"
  };
  for (const [name, id] of Object.entries(map)) {
    const el = document.getElementById(id);
    if (el) {
      if (pkgs[name]) {
        el.innerText = "설치됨 ✔";
        el.style.background = "rgba(16, 185, 129, 0.2)";
        el.style.color = "#10b981";
      } else {
        el.innerText = "미설치";
        el.style.background = "rgba(239, 68, 68, 0.2)";
        el.style.color = "#ef4444";
      }
    }
  }
}

async function generateRandomPorts() {
  try {
    const res = await fetch("/api/generate-ports");
    const data = await res.json();
    if (data.status === "success") {
      document.getElementById("input-ttyd-port").value = data.ttyd_port;
      document.getElementById("input-ssh-port").value = data.ssh_external_port;
      syncValues();
    }
  } catch (err) {
    const r1 = Math.floor(Math.random() * (59000 - 20000) + 20000);
    const r2 = Math.floor(Math.random() * (59000 - 20000) + 20000);
    document.getElementById("input-ttyd-port").value = r1;
    document.getElementById("input-ssh-port").value = r2;
    syncValues();
  }
}

async function executePackageCheckOrInstall() {
  const btn = document.getElementById("btn-simulate-install");
  const btnText = document.getElementById("install-btn-text");
  const consoleBox = document.getElementById("install-console");
  const consoleOutput = document.getElementById("console-output");

  btn.disabled = true;
  btnText.innerText = "⏳ 패키지 처리 진행 중...";
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
        consoleOutput.innerText += `- ${p.name}: ${p.status} ${p.path ? '(' + p.path + ')' : ''}\n`;
      });
      if (data.missing && data.missing.length > 0) {
        consoleOutput.innerText += `\n[권장 설치 커맨드]:\n${data.install_command}\n`;
      } else {
        consoleOutput.innerText += `\n✔ 모든 필수 바이너리가 시스템에 완벽히 구비되어 있습니다.\n`;
      }
    } else {
      const logs = [
        "Reading package lists... Done",
        "Building dependency tree... Done",
        "The following NEW packages will be installed: tmux ttyd nginx cloudflared",
        "Setting up tmux (3.4)...",
        "Setting up ttyd (1.7.4)...",
        "Setting up cloudflared connector...",
        "All packages installed successfully! (Simulation Mode)"
      ];
      for (let i = 0; i < logs.length; i++) {
        await new Promise(r => setTimeout(r, 200));
        consoleOutput.innerText += logs[i] + "\n";
      }
    }

    btnText.innerText = "✔ 패키지 점검 완료 (다음 단계로 진행하세요)";
  } catch (err) {
    consoleOutput.innerText = "오류 발생: " + err.message;
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
  const btn = document.getElementById("btn-deploy-services");
  const resDiv = document.getElementById("deploy-result");
  const ttydPort = document.getElementById("input-ttyd-port").value;
  const domain = document.getElementById("input-domain").value;

  btn.disabled = true;
  btn.innerText = "⏳ 서비스 등록 및 기동 중...";

  try {
    const res = await fetch("/api/deploy-services", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ttyd_port: ttydPort, domain, real_mode: isRealMode })
    });
    const data = await res.json();

    btn.innerText = "✔ 서비스 배포 완료";
    resDiv.style.display = "block";
    resDiv.innerHTML = `
      <strong>${data.message}</strong><br>
      - <code>ttyd.service</code>: [포트 ${ttydPort} 바인딩]<br>
      - <code>cloudflared.service</code>: [도메인 ${domain} 연동]<br>
      - <code>loginctl enable-linger</code>: [백그라운드 지속 활성화]
    `;

    document.getElementById("badge-ttyd").innerText = "Active";
    document.getElementById("badge-cf").innerText = "Active";
    document.getElementById("badge-linger").innerText = "Enabled";
  } catch (err) {
    resDiv.style.display = "block";
    resDiv.innerText = "배포 중 오류: " + err.message;
  } finally {
    btn.disabled = false;
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
      alert(data.message || "새 SSH 키페어가 발급되었습니다.");
    }
  } catch (err) {
    authStatus.innerText = "키 생성 오류: " + err.message;
  }
}

function copySnippet(elementId) {
  const text = document.getElementById(elementId).innerText;
  navigator.clipboard.writeText(text).then(() => {
    alert("명령어가 클립보드에 복사되었습니다!");
  });
}

function restartWizard() {
  document.querySelectorAll(".step-indicator").forEach(el => {
    el.classList.remove("completed");
  });
  changeStep(1);
}
