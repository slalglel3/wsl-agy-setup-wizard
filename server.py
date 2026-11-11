#!/usr/bin/env python3
"""
WSL2 AGY System - Web Setup Wizard (Simulation & Demo Server)
Pure Python 3 Standard Library - Zero external dependencies.
"""

import http.server
import json
import os
import random
import socket
import sys
import time
import urllib.parse

PORT = 8080
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")


def get_random_available_ports(count=2, min_port=20000, max_port=60000):
    """Find truly unused high-range ports or fallback to random simulation."""
    found = []
    attempts = 0
    while len(found) < count and attempts < 100:
        attempts += 1
        port = random.randint(min_port, max_port)
        if port in found:
            continue
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                found.append(port)
        except OSError:
            continue
    while len(found) < count:
        found.append(random.randint(min_port, max_port))
    return found


class WizardHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/inspect":
            self.send_json(self.mock_inspect())
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

        if parsed.path == "/api/install-packages":
            self.send_json(self.mock_install_packages())
        elif parsed.path == "/api/verify-token":
            self.send_json(self.mock_verify_token(req_data))
        elif parsed.path == "/api/deploy-services":
            self.send_json(self.mock_deploy_services(req_data))
        elif parsed.path == "/api/generate-keypair":
            self.send_json(self.mock_generate_keypair())
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

    def mock_inspect(self):
        user = os.environ.get("USER", "demo-user")
        home = os.environ.get("HOME", f"/home/{user}")
        return {
            "status": "success",
            "environment": {
                "os": "Linux (WSL2)",
                "distribution": "Ubuntu 24.04 LTS",
                "systemd": "Enabled (Active)",
                "user": user,
                "home": home,
                "windows_user": "WindowsUser",
                "python_version": sys.version.split()[0],
                "ports_status": "Ready for random allocation"
            },
            "checks": [
                {"name": "WSL2 Virtualization", "passed": True, "detail": "WSL2 Subsystem detected"},
                {"name": "Linux Distribution", "passed": True, "detail": "Ubuntu 22.04+ compatible"},
                {"name": "systemd Support", "passed": True, "detail": "User systemd daemon operational"},
                {"name": "Network Stack", "passed": True, "detail": "IPv4 / Loopback stack healthy"}
            ]
        }

    def mock_install_packages(self):
        return {
            "status": "success",
            "message": "All required packages installed successfully (Simulation Mode).",
            "packages": [
                {"name": "tmux", "status": "installed", "version": "3.4"},
                {"name": "ttyd", "status": "installed", "version": "1.7.4"},
                {"name": "nginx", "status": "installed", "version": "1.24.0"},
                {"name": "cloudflared", "status": "installed", "version": "2024.8.3"},
                {"name": "openssh-server", "status": "installed", "version": "9.6p1"}
            ]
        }

    def mock_verify_token(self, data):
        token = data.get("token", "").strip()
        domain = data.get("domain", "").strip()
        if not token or len(token) < 10:
            return {
                "status": "error",
                "message": "Token string is too short. Please paste a valid Cloudflare Tunnel token."
            }
        return {
            "status": "success",
            "message": f"Successfully connected to Cloudflare Edge Network. Ingress mapped to {domain or 'your-domain.pro'}."
        }

    def mock_deploy_services(self, data):
        return {
            "status": "success",
            "message": "Services registered and started via systemd user manager.",
            "services": [
                {"unit": "ttyd.service", "status": "active (running)", "port": data.get("ttyd_port", 34281)},
                {"unit": "cloudflared.service", "status": "active (running)", "ingress": data.get("domain", "your-domain.pro")},
                {"unit": "nginx.service", "status": "active (running)", "role": "Reverse Proxy (Read-Only Buffer)"}
            ]
        }

    def mock_generate_keypair(self):
        # Fake demo Ed25519 keypair for preview purposes only
        fake_pub = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIExampleFakeKeyDoNotUseInRealProductionForSimulationOnly user@wsl"
        fake_priv = (
            "-----BEGIN OPENSSH PRIVATE KEY-----\n"
            "b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW\n"
            "QyNTUxOQAAACCE...[SIMULATED DEMO KEY FOR PREVIEW ONLY]...=\n"
            "-----END OPENSSH PRIVATE KEY-----"
        )
        return {
            "status": "success",
            "public_key": fake_pub,
            "private_key": fake_priv,
            "qr_data": f"ssh://demo-user@your-domain.pro:28192?key=ed25519-demo"
        }


def run():
    port = PORT
    try:
        server = http.server.ThreadingHTTPServer(("0.0.0.0", port), WizardHandler)
    except OSError:
        port = 8081
        server = http.server.ThreadingHTTPServer(("0.0.0.0", port), WizardHandler)

    print("=" * 65)
    print("  WSL2 AGY System - Web Setup Wizard (Simulation & Preview Mode)")
    print("=" * 65)
    print(f"  * Web GUI URL : http://localhost:{port}")
    print(f"  * Mode        : 100% Safe Simulation (No system changes)")
    print("  * Press Ctrl+C to terminate the wizard server.")
    print("=" * 65)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nWizard server stopped.")


if __name__ == "__main__":
    run()
