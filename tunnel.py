import subprocess
import threading
import re
import time
import shutil
from pathlib import Path
from config import load_global_config


# ─────────────────────────────────────────────
# Cloudflare
# ─────────────────────────────────────────────

def _find_cloudflared() -> str | None:
    found = shutil.which("cloudflared")
    if found:
        return found
    candidates = [
        Path.home() / ".universal-dev-mcp" / "cloudflared",
        Path("/usr/local/bin/cloudflared"),
        Path("/usr/bin/cloudflared"),
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return None


def start_stable_tunnel(port: int, tunnel_name: str) -> tuple[subprocess.Popen | None, str | None]:
    binary = _find_cloudflared()
    if not binary:
        print("  ⚠ cloudflared not found. Run 'python setup_wizard.py' to install.")
        return None, None
    try:
        proc = subprocess.Popen(
            [binary, "tunnel", "run", "--url", f"http://localhost:{port}", tunnel_name],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        cfg = load_global_config()
        return proc, cfg.get("tunnel_url")
    except Exception as e:
        print(f"  ⚠ Cloudflare stable tunnel failed: {e}")
        return None, None


def start_quick_tunnel(port: int) -> tuple[subprocess.Popen | None, str | None]:
    binary = _find_cloudflared()
    if not binary:
        print("  ⚠ cloudflared not found. Run 'python setup_wizard.py' to install.")
        return None, None
    try:
        proc = subprocess.Popen(
            [binary, "tunnel", "--url", f"http://localhost:{port}"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        tunnel_url = None

        def read_url():
            nonlocal tunnel_url
            for line in proc.stderr:
                decoded = line.decode(errors="ignore")
                match = re.search(r"https://[\w\-]+\.(?:trycloudflare|cfargotunnel)\.com", decoded)
                if match:
                    tunnel_url = match.group()
                    break

        t = threading.Thread(target=read_url, daemon=True)
        t.start()
        t.join(timeout=20)
        return proc, tunnel_url
    except Exception as e:
        print(f"  ⚠ Cloudflare quick tunnel failed: {e}")
        return None, None


# ─────────────────────────────────────────────
# Tailscale
# ─────────────────────────────────────────────

def start_tailscale_tunnel(port: int) -> tuple[subprocess.Popen | None, str | None]:
    if not shutil.which("tailscale"):
        print("  ⚠ tailscale not found. Install: https://tailscale.com/install")
        return None, None
    try:
        subprocess.run(["sudo", "tailscale", "funnel", "reset"], capture_output=True, timeout=10)
        proc = subprocess.Popen(
            ["sudo", "tailscale", "funnel", str(port)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        time.sleep(3)

        cfg = load_global_config()
        tunnel_url = cfg.get("tunnel_url")

        if not tunnel_url:
            result = subprocess.run(
                ["tailscale", "funnel", "status"],
                capture_output=True, text=True, timeout=5,
            )
            match = re.search(r"https://[\w\-]+\.ts\.net", result.stdout + result.stderr)
            if match:
                tunnel_url = match.group()

        return proc, tunnel_url
    except Exception as e:
        print(f"  ⚠ Tailscale funnel failed: {e}")
        return None, None


# ─────────────────────────────────────────────
# Ngrok
# ─────────────────────────────────────────────

def start_ngrok_tunnel(port: int) -> tuple[subprocess.Popen | None, str | None]:
    if not shutil.which("ngrok"):
        print("  ⚠ ngrok not found. Install: https://ngrok.com/download")
        return None, None
    try:
        cfg = load_global_config()
        domain = cfg.get("ngrok_domain")

        cmd = ["ngrok", "http"]
        if domain:
            cmd += [f"--domain={domain}"]
        cmd.append(str(port))

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if domain:
            tunnel_url = f"https://{domain}"
        else:
            tunnel_url = None

            def read_ngrok_url():
                nonlocal tunnel_url
                for line in proc.stderr:
                    decoded = line.decode(errors="ignore")
                    match = re.search(r"https://[\w\-]+\.ngrok[\w\-\.]*\.app", decoded)
                    if match:
                        tunnel_url = match.group()
                        break

            t = threading.Thread(target=read_ngrok_url, daemon=True)
            t.start()
            t.join(timeout=15)

        return proc, tunnel_url
    except Exception as e:
        print(f"  ⚠ Ngrok tunnel failed: {e}")
        return None, None


# ─────────────────────────────────────────────
# Auto-select based on config
# ─────────────────────────────────────────────

def start_tunnel(port: int) -> tuple[subprocess.Popen | None, str | None]:
    cfg = load_global_config()
    provider = cfg.get("tunnel_provider", "cloudflare")

    if provider == "tailscale":
        print("  Starting Tailscale Funnel...")
        return start_tailscale_tunnel(port)

    if provider == "ngrok":
        print("  Starting Ngrok tunnel...")
        return start_ngrok_tunnel(port)

    if provider == "cloudflare":
        tunnel_name = cfg.get("tunnel_name")
        if tunnel_name:
            print("  Starting Cloudflare stable tunnel...")
            return start_stable_tunnel(port, tunnel_name)
        print("  Starting Cloudflare quick tunnel (URL changes on restart)...")
        return start_quick_tunnel(port)

    if provider in ("manual", "local_only", "none"):
        print("  Manual tunnel mode — ensure your tunnel is running externally.")
        return None, cfg.get("tunnel_url")

    print(f"  ⚠ Unknown tunnel_provider '{provider}'. Skipping tunnel.")
    return None, None
