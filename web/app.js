let currentStep = 1;
const totalSteps = 6;

document.addEventListener("DOMContentLoaded", () => {
  initEventListeners();
  fetchInitialInspection();
});

function initEventListeners() {
  document.getElementById("btn-prev").addEventListener("click", () => changeStep(currentStep - 1));
  document.getElementById("btn-next").addEventListener("click", () => changeStep(currentStep + 1));

  // Step 2: Random port generators
  document.getElementById("btn-re-random").addEventListener("click", generateRandomPorts);
  document.getElementById("btn-re-random-ssh").addEventListener("click", generateRandomPorts);

  // Step 3: Install simulator
  document.getElementById("btn-simulate-install").addEventListener("click", simulatePackageInstall);

  // Step 4: Token verify simulator
  document.getElementById("btn-verify-token").addEventListener("click", simulateTokenVerify);

  // Step 5: Service deploy simulator
  document.getElementById("btn-deploy-services").addEventListener("click", simulateServiceDeploy);

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

function changeStep(newStep) {
  if (newStep < 1 || newStep > 7) return;

  // Deactivate old step
  const oldSection = document.getElementById(`step-${currentStep}`);
  if (oldSection) oldSection.classList.remove("active");

  const oldIndicator = document.querySelector(`.step-indicator[data-step="${currentStep}"]`);
  if (oldIndicator) {
    oldIndicator.classList.remove("active");
    if (newStep > currentStep) oldIndicator.classList.add("completed");
  }

  currentStep = newStep;

  // Activate new step
  const newSection = document.getElementById(`step-${currentStep}`);
  if (newSection) newSection.classList.add("active");

  const newIndicator = document.querySelector(`.step-indicator[data-step="${currentStep}"]`);
  if (newIndicator) {
    newIndicator.classList.add("active");
    newIndicator.classList.remove("completed");
  }

  // Update footer buttons
  const btnPrev = document.getElementById("btn-prev");
  const btnNext = document.getElementById("btn-next");
  const counter = document.getElementById("curr-step-num");

  btnPrev.disabled = (currentStep === 1);

  if (currentStep <= totalSteps) {
    counter.innerText = currentStep;
    btnNext.innerText = (currentStep === totalSteps) ? "최종 완료 확인 ▶" : "다음 단계 ▶";
    btnNext.style.display = "inline-block";
  } else {
    // Step 7 (Completion celebration)
    counter.innerText = totalSteps;
    btnNext.style.display = "none";
  }

  syncValues();
}

function syncValues() {
  const domain = document.getElementById("input-domain").value || "myagy.example.com";
  const sshPort = document.getElementById("input-ssh-port").value || "29482";
  const ttydPort = document.getElementById("input-ttyd-port").value || "38491";

  // Step 2 PortProxy command update
  const cmdElem = document.getElementById("cmd-portproxy");
  if (cmdElem) {
    cmdElem.innerHTML = `<code>netsh interface portproxy add v4tov4 listenport=${sshPort} listenaddress=0.0.0.0 connectport=22 connectaddress=127.0.0.1</code>`;
  }

  // Step 6 Display updates
  const hostElem = document.getElementById("display-host");
  if (hostElem) hostElem.innerText = domain;

  const portElem = document.getElementById("display-port");
  if (portElem) portElem.innerText = sshPort;
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
    }
  } catch (err) {
    console.log("Inspection demo fallback");
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
    // Fallback simulation
    const r1 = Math.floor(Math.random() * (59000 - 20000) + 20000);
    const r2 = Math.floor(Math.random() * (59000 - 20000) + 20000);
    document.getElementById("input-ttyd-port").value = r1;
    document.getElementById("input-ssh-port").value = r2;
    syncValues();
  }
}

async function simulatePackageInstall() {
  const btn = document.getElementById("btn-simulate-install");
  const btnText = document.getElementById("install-btn-text");
  const consoleBox = document.getElementById("install-console");
  const consoleOutput = document.getElementById("console-output");

  btn.disabled = true;
  btnText.innerText = "⏳ 패키지 설치 진행 중 (시뮬레이션)...";
  consoleBox.style.display = "block";
  consoleOutput.innerText = "";

  const logs = [
    "Reading package lists... Done",
    "Building dependency tree... Done",
    "The following NEW packages will be installed: tmux ttyd nginx cloudflared",
    "Setting up tmux (3.4-1)...",
    "Setting up ttyd (1.7.4-1)...",
    "Setting up nginx (1.24.0)...",
    "Setting up cloudflared connector...",
    "Processing triggers for man-db...",
    "All packages installed successfully! (Safe Simulation Mode)"
  ];

  for (let i = 0; i < logs.length; i++) {
    await new Promise(r => setTimeout(r, 250));
    consoleOutput.innerText += logs[i] + "\n";
    consoleOutput.scrollTop = consoleOutput.scrollHeight;
  }

  btnText.innerText = "✔ 설치 완료됨 (다음 단계로 진행하세요)";
  btn.classList.remove("btn-primary");
  btn.classList.add("btn-secondary");
}

async function simulateTokenVerify() {
  const domain = document.getElementById("input-domain").value;
  const token = document.getElementById("input-token").value;
  const resultElem = document.getElementById("token-test-result");

  resultElem.innerText = "연결 테스트 중...";
  resultElem.className = "test-result";

  await new Promise(r => setTimeout(r, 600));

  resultElem.innerText = `✔ Cloudflare Ingress 연결 성공 (${domain})`;
  resultElem.className = "test-result success";
}

async function simulateServiceDeploy() {
  const btn = document.getElementById("btn-deploy-services");
  const resDiv = document.getElementById("deploy-result");

  btn.disabled = true;
  btn.innerText = "⏳ 템플릿 렌더링 및 systemd 유닛 등록 중...";

  await new Promise(r => setTimeout(r, 700));

  btn.innerText = "✔ 모든 서비스 활성화 완료";
  resDiv.style.display = "block";
  resDiv.innerHTML = `
    <strong>배포 완료:</strong><br>
    - <code>~/.config/systemd/user/ttyd.service</code> [Active: running]<br>
    - <code>~/.config/systemd/user/cloudflared.service</code> [Active: running]<br>
    - <code>loginctl enable-linger</code> [Active: persistent]
  `;
}

function copySnippet(elementId) {
  const text = document.getElementById(elementId).innerText;
  navigator.clipboard.writeText(text).then(() => {
    alert("클립보드에 복사되었습니다!");
  });
}

function restartWizard() {
  document.querySelectorAll(".step-indicator").forEach(el => {
    el.classList.remove("completed");
  });
  changeStep(1);
}
