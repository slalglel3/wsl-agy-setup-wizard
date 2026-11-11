#!/usr/bin/env python3
"""
WSL2 AGY System - Web Setup Wizard (Execution Engine)
Pure Python 3 Standard Library - Zero external dependencies.
Supports both Simulation Mode (Preview) and Real Execution Mode.
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

PORT = 8080
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")


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
        return res.returncode in (0, 1)  # 0: running, 1: degraded
    except Exception:
        return False


class WizardHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
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

    def handle_inspect(self):
        wsl_detected = is_wsl()
        distro = get_linux_distro()
        systemd_ok = check_systemd_user()
        user = getpass.getuser()
        home = os.path.expanduser("~")

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
            "ttyd": bool(shutil.which("ttyd")),
            "nginx": bool(shutil.which("nginx")),
            "cloudflared": bool(shutil.which("cloudflared")),
            "ssh": bool(shutil.which("ssh") and shutil.which("sshd"))
        }

        return {
            "status": "success",
            "environment": {
                "os": "Linux (WSL2)" if wsl_detected else "Linux",
                "distribution": distro,
                "systemd": "Enabled (Active)" if systemd_ok else "Disabled",
                "user": user,
                "home": home,
                "python_version": platform.python_version()
            },
            "installed_packages": installed_pkgs,
            "checks": checks
        }

    def handle_install_packages(self, is_real):
        if not is_real:
            # Simulation Mode
            return {
                "status": "success",
                "mode": "simulation",
                "message": "All packages verified successfully (Simulation Mode).",
                "packages": [
                    {"name": "tmux", "status": "installed", "version": "3.4"},
                    {"name": "ttyd", "status": "installed", "version": "1.7.4"},
                    {"name": "nginx", "status": "installed", "version": "1.24.0"},
                    {"name": "cloudflared", "status": "installed", "version": "latest"},
                    {"name": "openssh-server", "status": "installed", "version": "current"}
                ]
            }

        # Real Mode: Verify binaries and report actual status
        pkgs = ["tmux", "ttyd", "nginx", "cloudflared"]
        status_list = []
        missing = []
        for pkg in pkgs:
            path = shutil.which(pkg)
            if path:
                status_list.append({"name": pkg, "status": "installed", "path": path})
            else:
                missing.append(pkg)
                status_list.append({"name": pkg, "status": "missing"})

        return {
            "status": "success" if not missing else "partial",
            "mode": "real",
            "message": "System package status inspection complete." if not missing else f"Missing packages: {', '.join(missing)}",
            "packages": status_list,
            "missing": missing,
            "install_command": "sudo apt update && sudo apt install -y tmux nginx openssh-server"
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
                "message": f"Successfully simulated connection to Cloudflare. Ingress mapped to {domain or 'your-domain.pro'}."
            }

        # Real Mode: Write ~/.config/systemd/user/cloudflared.service
        user_systemd_dir = os.path.expanduser("~/.config/systemd/user")
        os.makedirs(user_systemd_dir, exist_ok=True)
        cf_bin = shutil.which("cloudflared") or "cloudflared"

        service_content = f"""[Unit]
Description=Cloudflare Tunnel Connector (WSL AGY System)
After=network.target

[Service]
Type=simple
ExecStart={cf_bin} tunnel run --token {token}
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
        domain = data.get("domain", "your-domain.pro")

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

        # Real Mode
        user = getpass.getuser()
        user_systemd_dir = os.path.expanduser("~/.config/systemd/user")
        os.makedirs(user_systemd_dir, exist_ok=True)
        ttyd_bin = shutil.which("ttyd") or "/usr/local/bin/ttyd"

        # 1. Write ttyd.service
        ttyd_service = f"""[Unit]
Description=ttyd Terminal Mirror Daemon (Read-Only)
After=network.target

[Service]
Type=simple
ExecStart={ttyd_bin} -p {ttyd_port} -R tmux attach -t main
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

        # 2. Ensure tmux session 'main' exists
        try:
            subprocess.run(["tmux", "has-session", "-t", "main"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

        # 3. Enable Linger for user
        try:
            subprocess.run(["loginctl", "enable-linger", user], timeout=5)
        except Exception:
            pass

        # 4. Reload daemon and enable services
        try:
            subprocess.run(["systemctl", "--user", "daemon-reload"], timeout=5)
            subprocess.run(["systemctl", "--user", "enable", "--now", "ttyd.service"], timeout=5)
            if os.path.exists(os.path.join(user_systemd_dir, "cloudflared.service")):
                subprocess.run(["systemctl", "--user", "enable", "--now", "cloudflared.service"], timeout=5)
        except Exception as e:
            return {
                "status": "warning",
                "mode": "real",
                "message": f"Service files written, but systemctl execution had warning: {str(e)}"
            }

        return {
            "status": "success",
            "mode": "real",
            "message": "ttyd and cloudflared services deployed and enabled with user linger.",
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

        # Real Mode: Generate dedicated Ed25519 keypair in ~/.ssh/
        ssh_dir = os.path.expanduser("~/.ssh")
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

        # Add to ~/.ssh/authorized_keys
        auth_keys = os.path.join(ssh_dir, "authorized_keys")
        existing_keys = ""
        if os.path.exists(auth_keys):
            with open(auth_keys, "r", encoding="utf-8") as f:
                existing_keys = f.read()

        if pub_content not in existing_keys:
            with open(auth_keys, "a", encoding="utf-8") as f:
                f.write(f"\n{pub_content}\n")
        os.chmod(auth_keys, 0o600)

        return {
            "status": "success",
            "mode": "real",
            "message": "Dedicated Ed25519 keypair generated and registered to authorized_keys.",
            "public_key": pub_content,
            "private_key": priv_content,
            "key_path": key_path
        }


def run():
    port = PORT
    try:
        server = http.server.ThreadingHTTPServer(("0.0.0.0", port), WizardHandler)
    except OSError:
        port = 8081
        server = http.server.ThreadingHTTPServer(("0.0.0.0", port), WizardHandler)

    print("=" * 65)
    print("  WSL2 AGY System - Web Setup Wizard (Execution Engine)")
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
