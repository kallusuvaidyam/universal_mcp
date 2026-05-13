import subprocess
import threading
import re
import time
import sys
import os
from pathlib import Path
from config import load_global_config


def _find_cloudflared() -> str | None:
    """Find cloudflared binary path."""
    import shutil
    found = shutil.which("cloudflared")
    if found:
        return found
    # Check common locations
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
    """Start a named Cloudflare stable tunnel (requires account setup)."""
    binary = _find_cloudflared()
    if not binary:
        print("  ⚠ cloudflared not found. Run 'python setup_wizard.py' to install.")
        return None, None

    try:
        proc = subprocess.Popen(
            [binary, "tunnel", "run", "--url", f"http://localhost:{port}", tunnel_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        # Named tunnel URL is pre-configured — read from global config
        cfg = load_global_config()
        tunnel_url = cfg.get("tunnel_url")
        return proc, tunnel_url
    except Exception as e:
        print(f"  ⚠ Tunnel start failed: {e}")
        return None, None


def start_quick_tunnel(port: int) -> tuple[subprocess.Popen | None, str | None]:
    """Start a Cloudflare quick tunnel (no account needed, URL changes each time)."""
    binary = _find_cloudflared()
    if not binary:
        print("  ⚠ cloudflared not found. Run 'python setup_wizard.py' to install.")
        return None, None

    try:
        proc = subprocess.Popen(
            [binary, "tunnel", "--url", f"http://localhost:{port}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        tunnel_url = None
        start_time = time.time()

        # Read stderr to find the URL (cloudflared prints URL to stderr)
        def read_url():
            nonlocal tunnel_url
            for line in proc.stderr:
                decoded = line.decode(errors="ignore")
                match = re.search(
                    r"https://[\w\-]+\.(?:trycloudflare|cfargotunnel)\.com", decoded
                )
                if match:
                    tunnel_url = match.group()
                    break

        t = threading.Thread(target=read_url, daemon=True)
        t.start()
        t.join(timeout=20)  # Wait max 20 seconds for URL

        return proc, tunnel_url
    except Exception as e:
        print(f"  ⚠ Quick tunnel failed: {e}")
        return None, None


def start_tunnel(port: int) -> tuple[subprocess.Popen | None, str | None]:
    """Auto-pick tunnel type based on global config."""
    cfg = load_global_config()
    tunnel_name = cfg.get("tunnel_name")

    if tunnel_name:
        print("  Starting Cloudflare stable tunnel...")
        return start_stable_tunnel(port, tunnel_name)
    else:
        print("  Starting Cloudflare quick tunnel (URL will change on restart)...")
        print("  Tip: Run 'python setup_wizard.py' to configure stable tunnel.")
        return start_quick_tunnel(port)
