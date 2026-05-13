"""
Universal Dev MCP — Setup Wizard
Non-tech user friendly one-time setup.
Run: python setup_wizard.py
"""
import os
import sys
import json
import subprocess
import platform
from pathlib import Path

CONFIG_DIR = Path.home() / ".universal-dev-mcp"
CONFIG_FILE = CONFIG_DIR / "config.json"


def print_banner():
    print("\n" + "="*55)
    print("  Universal Dev MCP — Setup Wizard")
    print("="*55)
    print("  Yeh wizard aapka ek baar ka setup karega.")
    print("  Baad mein sirf: python main.py start")
    print("="*55 + "\n")


def ask(prompt: str, default: str = "") -> str:
    if default:
        val = input(f"  {prompt} [{default}]: ").strip()
        return val if val else default
    return input(f"  {prompt}: ").strip()


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    val = input(f"  {prompt} {suffix}: ").strip().lower()
    if not val:
        return default
    return val in ("y", "yes", "haan", "ha")


def check_python():
    print("📋 Step 1: Python check...")
    v = sys.version_info
    if v.major < 3 or (v.major == 3 and v.minor < 10):
        print(f"  ❌ Python 3.10+ chahiye. Aapke paas: {v.major}.{v.minor}")
        sys.exit(1)
    print(f"  ✅ Python {v.major}.{v.minor} — OK\n")


def install_requirements():
    print("📋 Step 2: Dependencies install karo...")
    req_file = Path(__file__).parent / "requirements.txt"
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(req_file), "-q"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  ❌ Install failed:\n{result.stderr}")
        sys.exit(1)
    print("  ✅ Dependencies installed\n")


def install_cloudflared():
    print("📋 Step 3: Cloudflare Tunnel setup...")

    import shutil
    if shutil.which("cloudflared"):
        print("  ✅ cloudflared already installed\n")
        return True

    print("  cloudflared nahi mila. Install karna chahoge?")
    print("  (Cloudflare tunnel ke liye zaruri hai)")
    if not ask_yes_no("  Install cloudflared?"):
        print("  ⚠ Skip kiya. Tunnel kaam nahi karega.\n")
        return False

    system = platform.system().lower()
    machine = platform.machine().lower()

    urls = {
        ("linux", "x86_64"): "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64",
        ("linux", "aarch64"): "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64",
        ("darwin", "x86_64"): "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-amd64.tgz",
        ("darwin", "arm64"): "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-arm64.tgz",
    }

    url = urls.get((system, machine))
    if not url:
        print(f"  ❌ Aapke OS ({system}/{machine}) ke liye auto-install nahi. Manual install karo:")
        print("  https://developers.cloudflare.com/cloudflared/get-started/")
        return False

    dest = CONFIG_DIR / "cloudflared"
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    print(f"  Downloading cloudflared...")
    result = subprocess.run(["curl", "-L", "-o", str(dest), url], capture_output=True)
    if result.returncode == 0:
        dest.chmod(0o755)
        # Add to PATH for this session
        os.environ["PATH"] = str(CONFIG_DIR) + ":" + os.environ.get("PATH", "")
        print(f"  ✅ cloudflared installed at: {dest}\n")
        return True
    else:
        print("  ❌ Download failed. Manual install karo.")
        return False


def setup_cloudflare_stable():
    """Guide user through stable tunnel setup."""
    print("📋 Step 4: Cloudflare Stable Tunnel configure karo...")
    print()
    print("  Stable tunnel ke liye ek free Cloudflare account chahiye.")
    print("  Isse aapka URL hamesha same rahega (server restart ke baad bhi).")
    print()

    if not ask_yes_no("  Stable tunnel setup karna chahoge?"):
        print("  ⚠ Quick tunnel use hoga — URL har restart par change hogi.\n")
        return {}

    print()
    print("  ── Instructions ──")
    print("  1. https://cloudflare.com par free account banao")
    print("  2. Terminal mein: cloudflared login")
    print("     (Browser khulega — allow karo)")
    print("  3. Tunnel create karo:")
    print("     cloudflared tunnel create my-mcp")
    print("  4. Ye URL note karo: <something>.cfargotunnel.com")
    print()
    input("  Jab ye sab ho jaye, Enter dabao... ")
    print()

    tunnel_name = ask("  Tunnel naam kya rakha? (e.g. my-mcp)", "my-mcp")
    tunnel_url = ask("  Tunnel URL kya mila? (e.g. abc123.cfargotunnel.com)")

    if not tunnel_url.startswith("https://"):
        tunnel_url = "https://" + tunnel_url

    print(f"\n  ✅ Saved: {tunnel_url}\n")
    return {"tunnel_name": tunnel_name, "tunnel_url": tunnel_url}


def setup_email():
    """Optional email setup for OTP."""
    print("📋 Step 5: Email setup (OTP ke liye)...")
    print("  Email setup nahi karne par OTP terminal mein print hoga.")
    print()

    if not ask_yes_no("  Email se OTP chahiye?", default=False):
        print("  ⚠ OTP terminal mein dikhega — OK\n")
        return {}

    smtp_host = ask("  SMTP Host (e.g. smtp.gmail.com)", "smtp.gmail.com")
    smtp_port = ask("  SMTP Port", "587")
    from_email = ask("  Email address")
    password = ask("  Email password / App password")

    return {
        "email": {
            "smtp_host": smtp_host,
            "smtp_port": int(smtp_port),
            "from_email": from_email,
            "smtp_password": password,
        }
    }


def save_config(config: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def print_next_steps(config: dict):
    tunnel_url = config.get("tunnel_url", "")
    print("\n" + "="*55)
    print("  ✅ SETUP COMPLETE!")
    print("="*55)
    print()
    print("  Roz server start karo:")
    print()
    print("    python main.py start --project /aapka/project/path")
    print()
    print("  Claude.ai mein add karo:")
    print("    Settings → Integrations → Custom MCP")
    print()
    print("  Local URL:   http://localhost:8080")
    if tunnel_url:
        print(f"  Remote URL:  {tunnel_url}")
    print()
    print("  ✅ Ek baar add karo — hamesha kaam karega!")
    print("="*55 + "\n")


def run():
    print_banner()
    check_python()
    install_requirements()
    cf_installed = install_cloudflared()

    config = {}
    if cf_installed:
        tunnel_cfg = setup_cloudflare_stable()
        config.update(tunnel_cfg)

    email_cfg = setup_email()
    config.update(email_cfg)

    config["default_port"] = 8080
    save_config(config)
    print_next_steps(config)


if __name__ == "__main__":
    run()
