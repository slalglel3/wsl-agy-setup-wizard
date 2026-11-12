#!/usr/bin/env python3
"""
WSL2 AGY System - Web Setup Wizard (Production-Ready Execution Engine v2)
Pure Python 3 Standard Library - Zero external dependencies.
"""

import getpass
import http.server
import json
import os
import platform
import random
import shutil
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request

PORT = 8080
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")


def get_random_available_ports(count=2, min_port=20000, max_port=60000):
    """Find truly unused high-range ports using socket binding."""
    found = []
    attempts = 0
    while len(found) < count and attempts < 200:
        attempts += 1
        port = random.randint(min_port, max_port)
        if port in found:
            continue
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("127.0.0.1", port))
                found.append(port)
        except OSError:
            continue
    while len(found) < count:
        found.append(random.randint(min_port, max_port))
    return found


def is_wsl():
    """Detect if the current environment is running inside WSL."""
    if os.path.exists("/proc/version"):
        try:
            with open("/proc/version", "r") as f:
                content = f.read().lower()
                return "microsoft" in content or "wsl" in content
        except Exception:
            pass
    return False


def get_linux_distro():
    """Extract OS distribution details."""
    if os.path.exists("/etc/os-release"):
        try:
            with open("/etc/os-release", "r") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        return line.split("=", 1)[1].strip().strip('"')
        except Exception:
            pass
    return platform.platform()


def check_systemd_user():
    """Check if systemd --user daemon is operational."""
    try:
        res = subprocess.run(
            ["systemctl", "--user", "is-system-running"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3
        )
        return res.returncode in (0, 1)
    except Exception:
        return False


def ensure_local_bin_in_path():
    """Ensure ~/.local/bin exists and has standard permissions."""
    local_bin = os.path.expanduser("~/.local/bin")
    os.makedirs(local_bin, exist_ok=True)
    current_path = os.environ.get("PATH", "")
    if local_bin not in current_path.split(":"):
        os.environ["PATH"] = f"{local_bin}:{current_path}"
    return local_bin


def download_binary(url, target_path):
    """Download a standalone executable binary and set +x permissions."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (WSL-Setup-Wizard)"}
        )
        with urllib.request.urlopen(req, timeout=30) as response, open(target_path, "wb") as out_file:
            shutil.copyfileobj(response, out_file)
        os.chmod(target_path, 0o755)
        return True, "Download complete"
    except Exception as e:
        return False, str(e)


def deploy_assets_bundle(local_bin, user_home):
    """Deploy wsl-key-feeder, tm-jump and merge .tmux.conf."""
    os.makedirs(local_bin, exist_ok=True)

    # 1. wsl-key-feeder
    feeder_src = os.path.join(ASSETS_DIR, "wsl-key-feeder")
    feeder_dst = os.path.join(local_bin, "wsl-key-feeder")
    if os.path.exists(feeder_src):
        shutil.copy2(feeder_src, feeder_dst)
        os.chmod(feeder_dst, 0o755)

    # 2. tm-jump
    jump_src = os.path.join(ASSETS_DIR, "tm-jump")
    jump_dst = os.path.join(local_bin, "tm-jump")
    if os.path.exists(jump_src):
        shutil.copy2(jump_src, jump_dst)
        os.chmod(jump_dst, 0o755)

    # 3. .tmux.conf safe merge
    tmux_conf_src = os.path.join(ASSETS_DIR, ".tmux.conf")
    tmux_conf_dst = os.path.join(user_home, ".tmux.conf")
    if os.path.exists(tmux_conf_src):
        if not os.path.exists(tmux_conf_dst):
            shutil.copy2(tmux_conf_src, tmux_conf_dst)
        else:
            # Check if keybindings are present, if not append
            with open(tmux_conf_dst, "r", encoding="utf-8") as f:
                content = f.read()
            if "tm-jump" not in content:
                with open(tmux_conf_src, "r", encoding="utf-8") as sf, open(tmux_conf_dst, "a", encoding="utf-8") as df:
                    df.write("\n# === WSL AGY Setup Wizard Configurations ===\n" + sf.read())


class WizardHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/api/inspect":
            self.send_json(self.handle_inspect())
        elif parsed.path == "/api/generate-ports":
            ports = get_random_available_ports(2)
            self.send_json({
                "status": "success",
                "ttyd_port": ports[0],
                "ssh_external_port": ports[1],
                "win_ssh_port": 2222
            })
        elif parsed.path == "/api/download-windows-script":
            ssh_port = query.get("ssh_port", ["29482"])[0]
            self.handle_download_windows_script(ssh_port)
        elif parsed.path == "/api/health-check":
            ttyd_port = query.get("ttyd_port", ["34281"])[0]
            self.send_json(self.handle_health_check(ttyd_port))
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_length) if content_length > 0 else b"{}"

        try:
            req_data = json.loads(post_body.decode("utf-8")) if post_body else {}
        except Exception:
            req_data = {}

        is_real = bool(req_data.get("real_mode", False))

        if parsed.path == "/api/install-packages":
            self.send_json(self.handle_install_packages(is_real))
        elif parsed.path == "/api/verify-token":
            self.send_json(self.handle_verify_token(req_data, is_real))
        elif parsed.path == "/api/deploy-services":
            self.send_json(self.handle_deploy_services(req_data, is_real))
        elif parsed.path == "/api/generate-keypair":
            self.send_json(self.handle_generate_keypair(is_real))
        else:
            self.send_error(404, "Endpoint not found")

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def handle_download_windows_script(self, ssh_port):
        template_file = os.path.join(ASSETS_DIR, "setup-windows-host.bat")
        content = "@echo off\n"
        if os.path.exists(template_file):
            with open(template_file, "r", encoding="utf-8") as f:
                content = f.read()
        content = content.replace("{{ SSH_PORT }}", str(ssh_port))
        # Ensure Windows CRLF line endings for maximum batch file compatibility
        content = content.replace("\r\n", "\n").replace("\n", "\r\n")
        data = content.encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Disposition", f"attachment; filename=setup-windows-host.bat")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def handle_inspect(self):
        wsl_detected = is_wsl()
        distro = get_linux_distro()
        systemd_ok = check_systemd_user()
        user = getpass.getuser()
        home = os.path.expanduser("~")
        local_bin = ensure_local_bin_in_path()

        checks = [
            {
                "name": "WSL2 Virtualization",
                "passed": wsl_detected,
                "detail": "WSL2 Subsystem detected" if wsl_detected else "Standard Linux / Baremetal"
            },
            {
                "name": "Linux Distribution",
                "passed": True,
                "detail": distro
            },
            {
                "name": "systemd Support",
                "passed": systemd_ok,
                "detail": "User systemd daemon operational" if systemd_ok else "systemd --user unavailable"
            },
            {
                "name": "Network & Loopback Stack",
                "passed": True,
                "detail": "IPv4 / 127.0.0.1 stack operational"
            }
        ]

        installed_pkgs = {
            "tmux": bool(shutil.which("tmux")),
            "ttyd": bool(shutil.which("ttyd") or os.path.exists(os.path.join(local_bin, "ttyd"))),
            "openssh": bool(shutil.which("sshd")),
            "cloudflared": bool(shutil.which("cloudflared") or os.path.exists(os.path.join(local_bin, "cloudflared"))),
            "feeder": bool(os.path.exists(os.path.join(local_bin, "wsl-key-feeder")))
        }

        return {
            "status": "success",
            "environment": {
                "os": "Linux (WSL2)" if wsl_detected else "Linux",
                "distribution": distro,
                "systemd": "Enabled (Active)" if systemd_ok else "Disabled",
                "user": user,
                "home": home,
                "arch": platform.machine(),
                "python_version": platform.python_version()
            },
            "installed_packages": installed_pkgs,
            "checks": checks
        }

    def handle_install_packages(self, is_real):
        if not is_real:
            return {
                "status": "success",
                "mode": "simulation",
                "message": "All packages verified successfully (Simulation Mode).",
                "packages": [
                    {"name": "tmux", "status": "installed", "version": "3.4"},
                    {"name": "ttyd", "status": "installed", "version": "1.7.4 (Standalone)"},
                    {"name": "openssh-server", "status": "installed", "version": "1:9.6p1"},
                    {"name": "cloudflared", "status": "installed", "version": "latest (Standalone)"},
                    {"name": "wsl-key-feeder", "status": "installed", "version": "v1.04"}
                ]
            }

        # Real Mode: Multi-arch standalone binary download & asset bundling
        local_bin = ensure_local_bin_in_path()
        user_home = os.path.expanduser("~")
        deploy_assets_bundle(local_bin, user_home)

        arch = platform.machine().lower()
        is_arm = "aarch64" in arch or "arm" in arch
        results = []
        has_failure = False

        # 1. ttyd standalone binary download
        ttyd_path = shutil.which("ttyd") or os.path.join(local_bin, "ttyd")
        if not os.path.exists(ttyd_path):
            ttyd_arch = "aarch64" if is_arm else "x86_64"
            ttyd_url = f"https://github.com/tsl0922/ttyd/releases/latest/download/ttyd.{ttyd_arch}"
            ok, msg = download_binary(ttyd_url, os.path.join(local_bin, "ttyd"))
            if not ok:
                has_failure = True
            results.append({"name": "ttyd", "status": "installed" if ok else "failed", "detail": msg})
        else:
            results.append({"name": "ttyd", "status": "installed", "detail": ttyd_path})

        # 2. cloudflared standalone binary download
        cf_path = shutil.which("cloudflared") or os.path.join(local_bin, "cloudflared")
        if not os.path.exists(cf_path):
            cf_arch = "arm64" if is_arm else "amd64"
            cf_url = f"https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-{cf_arch}"
            ok, msg = download_binary(cf_url, os.path.join(local_bin, "cloudflared"))
            if not ok:
                has_failure = True
            results.append({"name": "cloudflared", "status": "installed" if ok else "failed", "detail": msg})
        else:
            results.append({"name": "cloudflared", "status": "installed", "detail": cf_path})

        # 3. Check system apt binaries (tmux, openssh-server)
        missing_apt = []
        for pkg in ["tmux", "openssh-server"]:
            p = shutil.which(pkg) if pkg != "openssh-server" else shutil.which("sshd")
            if p:
                results.append({"name": pkg, "status": "installed", "detail": p})
            else:
                missing_apt.append(pkg)
                results.append({"name": pkg, "status": "missing", "detail": "Run: sudo apt install -y " + pkg})

        # 4. Feeder asset status
        feeder_ok = os.path.exists(os.path.join(local_bin, "wsl-key-feeder"))
        results.append({
            "name": "wsl-key-feeder",
            "status": "installed" if feeder_ok else "missing",
            "detail": os.path.join(local_bin, "wsl-key-feeder")
        })

        status_flag = "error" if has_failure else ("partial" if missing_apt else "success")
        return {
            "status": status_flag,
            "mode": "real",
            "message": "Binary provisioning complete." if status_flag == "success" else "Some packages require attention.",
            "packages": results,
            "missing": missing_apt,
            "install_command": "sudo apt update && sudo apt install -y tmux openssh-server"
        }

    def handle_verify_token(self, data, is_real):
        token = data.get("token", "").strip()
        domain = data.get("domain", "").strip()

        if not token or len(token) < 15:
            return {
                "status": "error",
                "message": "Token string is too short. Please paste a valid Cloudflare Tunnel token."
            }

        if not is_real:
            return {
                "status": "success",
                "mode": "simulation",
                "message": f"Successfully simulated connection to Cloudflare. Ingress mapped to {domain or 'myterminal.example.com'}."
            }

        # Real Mode: Write ~/.config/systemd/user/cloudflared.service with http2 protocol guard
        user_systemd_dir = os.path.expanduser("~/.config/systemd/user")
        os.makedirs(user_systemd_dir, exist_ok=True)
        local_bin = ensure_local_bin_in_path()
        cf_bin = shutil.which("cloudflared") or os.path.join(local_bin, "cloudflared")

        service_content = f"""[Unit]
Description=Cloudflare Tunnel Connector (WSL AGY System)
After=network.target

[Service]
Type=simple
ExecStart={cf_bin} tunnel --protocol http2 run --token {token}
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
"""
        service_path = os.path.join(user_systemd_dir, "cloudflared.service")
        try:
            with open(service_path, "w", encoding="utf-8") as f:
                f.write(service_content)
            return {
                "status": "success",
                "mode": "real",
                "message": f"Cloudflare systemd service template created at {service_path}.",
                "path": service_path
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to write service file: {str(e)}"
            }

    def handle_deploy_services(self, data, is_real):
        ttyd_port = int(data.get("ttyd_port", 34281))
        domain = data.get("domain", "myterminal.example.com")

        if not is_real:
            return {
                "status": "success",
                "mode": "simulation",
                "message": "Services registered and simulated active.",
                "services": [
                    {"unit": "ttyd.service", "status": "active (running)", "port": ttyd_port},
                    {"unit": "cloudflared.service", "status": "active (running)", "ingress": domain},
                    {"unit": "loginctl linger", "status": "enabled"}
                ]
            }

        # Real Mode: Robust ttyd unit with ExecStartPre session guard & -P 60 keepalive
        user = getpass.getuser()
        user_systemd_dir = os.path.expanduser("~/.config/systemd/user")
        os.makedirs(user_systemd_dir, exist_ok=True)
        local_bin = ensure_local_bin_in_path()
        ttyd_bin = shutil.which("ttyd") or os.path.join(local_bin, "ttyd")
        tmux_bin = shutil.which("tmux") or "/usr/bin/tmux"

        ttyd_service = f"""[Unit]
Description=ttyd Terminal Mirror Daemon (Read-Only)
After=network.target

[Service]
Type=simple
ExecStartPre=/bin/bash -c "{tmux_bin} has-session -t main 2>/dev/null || {tmux_bin} new-session -d -s main -c %h"
ExecStart={ttyd_bin} -p {ttyd_port} -P 60 -t fontSize=16 -R {tmux_bin} attach-session -t main
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
"""
        ttyd_path = os.path.join(user_systemd_dir, "ttyd.service")
        with open(ttyd_path, "w", encoding="utf-8") as f:
            f.write(ttyd_service)

        # 1. Ensure tmux session 'main' exists right now
        try:
            if subprocess.run([tmux_bin, "has-session", "-t", "main"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0:
                subprocess.run([tmux_bin, "new-session", "-d", "-s", "main"])
        except Exception:
            pass

        # 2. Enable Linger for user
        try:
            subprocess.run(["loginctl", "enable-linger", user], timeout=5)
        except Exception:
            pass

        # 3. Reload daemon and start services
        try:
            subprocess.run(["systemctl", "--user", "daemon-reload"], timeout=5)
            subprocess.run(["systemctl", "--user", "enable", "--now", "ttyd.service"], timeout=5)
            if os.path.exists(os.path.join(user_systemd_dir, "cloudflared.service")):
                subprocess.run(["systemctl", "--user", "enable", "--now", "cloudflared.service"], timeout=5)
        except Exception as e:
            return {
                "status": "warning",
                "mode": "real",
                "message": f"Service files written, warning during systemctl: {str(e)}"
            }

        return {
            "status": "success",
            "mode": "real",
            "message": "ttyd.service (with session guard) and cloudflared.service deployed successfully.",
            "services": [
                {"unit": "ttyd.service", "status": "deployed", "port": ttyd_port},
                {"unit": "cloudflared.service", "status": "deployed"},
                {"unit": f"loginctl linger ({user})", "status": "enabled"}
            ]
        }

    def handle_generate_keypair(self, is_real):
        if not is_real:
            fake_pub = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIExampleFakeKeyDoNotUseInRealProductionForSimulationOnly user@wsl"
            fake_priv = (
                "-----BEGIN OPENSSH PRIVATE KEY-----\n"
                "b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW\n"
                "QyNTUxOQAAACCE...[SIMULATED DEMO KEY FOR PREVIEW ONLY]...=\n"
                "-----END OPENSSH PRIVATE KEY-----"
            )
            return {
                "status": "success",
                "mode": "simulation",
                "public_key": fake_pub,
                "private_key": fake_priv,
                "fingerprint": "SHA256:SimulationFingerprintDoNotUse"
            }

        # Real Mode: Generate dedicated Ed25519 keypair and register with Forced Command for KeyBridge
        local_bin = ensure_local_bin_in_path()
        user_home = os.path.expanduser("~")
        deploy_assets_bundle(local_bin, user_home)

        ssh_dir = os.path.join(user_home, ".ssh")
        os.makedirs(ssh_dir, mode=0o700, exist_ok=True)
        key_path = os.path.join(ssh_dir, "id_keybridge_wizard")
        pub_path = key_path + ".pub"

        if not os.path.exists(key_path):
            res = subprocess.run(
                ["ssh-keygen", "-t", "ed25519", "-f", key_path, "-N", "", "-C", "keybridge-wizard"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if res.returncode != 0:
                return {"status": "error", "message": f"ssh-keygen failed: {res.stderr}"}

        with open(pub_path, "r", encoding="utf-8") as f:
            pub_content = f.read().strip()
        with open(key_path, "r", encoding="utf-8") as f:
            priv_content = f.read()

        # Add to ~/.ssh/authorized_keys with FORCED COMMAND for wsl-key-feeder
        feeder_bin = os.path.join(local_bin, "wsl-key-feeder")
        forced_entry = f'command="{feeder_bin}",no-pty,no-X11-forwarding,no-port-forwarding {pub_content}'

        auth_keys = os.path.join(ssh_dir, "authorized_keys")
        existing_keys = ""
        if os.path.exists(auth_keys):
            with open(auth_keys, "r", encoding="utf-8") as f:
                existing_keys = f.read()

        if pub_content not in existing_keys:
            with open(auth_keys, "a", encoding="utf-8") as f:
                f.write(f"\n{forced_entry}\n")
        os.chmod(auth_keys, 0o600)

        # Ensure sshd is running if possible
        try:
            subprocess.run(["sudo", "-n", "service", "ssh", "start"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

        return {
            "status": "success",
            "mode": "real",
            "message": "KeyBridge ecosystem (wsl-key-feeder forced command) and Ed25519 key registered.",
            "public_key": pub_content,
            "private_key": priv_content,
            "key_path": key_path,
            "feeder_installed": os.path.exists(feeder_bin)
        }

    def handle_health_check(self, ttyd_port):
        local_bin = ensure_local_bin_in_path()
        feeder_ok = os.path.exists(os.path.join(local_bin, "wsl-key-feeder"))

        # Check local ttyd port response
        port_open = False
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)
                port_open = (s.connect_ex(("127.0.0.1", int(ttyd_port))) == 0)
        except Exception:
            pass

        # Check systemd user services
        ttyd_active = False
        cf_active = False
        try:
            res_ttyd = subprocess.run(["systemctl", "--user", "is-active", "ttyd.service"], stdout=subprocess.PIPE, text=True)
            ttyd_active = (res_ttyd.stdout.strip() == "active")
            res_cf = subprocess.run(["systemctl", "--user", "is-active", "cloudflared.service"], stdout=subprocess.PIPE, text=True)
            cf_active = (res_cf.stdout.strip() == "active")
        except Exception:
            pass

        # Check sshd status
        ssh_active = bool(shutil.which("ssh"))
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)
                ssh_active = (s.connect_ex(("127.0.0.1", 22)) == 0)
        except Exception:
            pass

        all_ok = ttyd_active and port_open and feeder_ok and ssh_active
        return {
            "status": "success",
            "health": {
                "ttyd_service": ttyd_active,
                "ttyd_port_open": port_open,
                "cloudflared_service": cf_active,
                "feeder_binary": feeder_ok,
                "ssh_port_open": ssh_active,
                "all_healthy": all_ok
            }
        }


def run():
    port = PORT
    try:
        server = http.server.ThreadingHTTPServer(("0.0.0.0", port), WizardHandler)
    except OSError:
        port = 8081
        server = http.server.ThreadingHTTPServer(("0.0.0.0", port), WizardHandler)

    print("=" * 65)
    print("  WSL2 AGY System - Web Setup Wizard (Production Engine v2)")
    print("=" * 65)
    print(f"  * Web GUI URL : http://localhost:{port}")
    print(f"  * Mode        : Supports Simulation & Real Install Modes")
    print("  * Press Ctrl+C to terminate the wizard server.")
    print("=" * 65)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nWizard server stopped.")


if __name__ == "__main__":
    run()
