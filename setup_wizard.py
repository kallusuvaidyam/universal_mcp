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
import shutil
from pathlib import Path

# Path.home():- /home/kk/
# Path.home() / ".universal-dev-mcp":- /home/kk/.universal-dev-mcp
CONFIG_DIR = Path.home() / ".universal-dev-mcp"

# /home/kk/.universal-dev-mcp/config.json
CONFIG_FILE = CONFIG_DIR / "config.json"


def print_banner():
    print("\n" + "=" * 55)
    print("  Universal Dev MCP — Setup Wizard")
    print("=" * 55)
    print("  This wizard will perform a one-time setup.")
    print("  Afterward, simply run: `python main.py`")
    print("=" * 55 + "\n")


def ask(prompt: str, default: str = "") -> str:
    if default:
        val = input(f"  {prompt} [{default}]: ").strip()
        return val if val else default
    return input(f"  {prompt}: ").strip()


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    # default = True means default answer is Yes, so suffix should be [Y/n]
    suffix = "[Y/n]" if default else "[y/N]"
    val = input(f"  {prompt} {suffix}: ").strip().lower()
    if not val:
        return default
    return val in ("y", "yes", "haan", "ha")


def ask_choice(prompt: str, options: list[tuple[str, str]]) -> str:
    """Show numbered options and return chosen key."""
    print(f"\n  {prompt}")
    for i, (key, label) in enumerate(options, 1):
        print(f"  {i}. {label}")
    while True:
        val = input(f"\n  Please enter your choice (1-{len(options)}): ").strip()
        if val.isdigit() and 1 <= int(val) <= len(options):
            return options[int(val) - 1][0]
        print(f"  ❌ Galat input. 1 se {len(options)} ke beech number enter karo.")


# ─────────────────────────────────────────────
# STEP 1 — Python check
# ─────────────────────────────────────────────

def check_python():
    print("📋 Step 1: Python check...")
    # sys:- Python ka built-in module hai.
    # sys.version = Python version string
    # sys.version_info:- Python version ko structured form me access karne ka object (jisse major, minor, micro alag-alag milte hain)
    # sys.platform:- linux, windows etc.
    # sys.argv:- jab user koi command run karta hai to usko ye store karta hai list me word wise split karke ex. command:- python3 main.py start, output:- [main.py, start]
    v = sys.version_info
    if v.major < 3 or (v.major == 3 and v.minor < 10):
        print(f"  ❌ We should Python 3.10+. You have: {v.major}.{v.minor}")
        # sys.exit():- programm close karna, sys.exit(1):- matlab programt code set karna, 0-success, 1-something error
        sys.exit(1) 
    print(f"  ✅ Python {v.major}.{v.minor} — OK\n")


# ─────────────────────────────────────────────
# STEP 2 — Dependencies
# ─────────────────────────────────────────────

def install_requirements():
    print("📋 Step 2: Dependencies install karo...")
    # __file__:- Returns the current Python file's path. in str
    # Path(__file__):- Returns the current Python file's path. in Path object
    # Path(__file__).parent:- Returns the current Python file's path parent directory. in Path object
    # Path(__file__).parent / "requirements.txt":- Create a new Path in the same directory as the current file, pointing to "requirements.txt" but not checking if it exists. in Path object
    req_file = Path(__file__).parent / "requirements.txt"
    # subprocess.run:- Execute an external command from Python. Here, it runs pip to install dependencies from the requirements.txt file.
    result = subprocess.run(
        # sys.executable:- like this /usr/bin/python3, so /usr/bin/python3 -m pip install -r requirements.txt -q
        # -m:- Tells Python to run a module.
        # pip:- The module used for installing Python packages.
        # install:- The pip command to install packages.
        # -r:- Tells pip to install from a requirements file.
        # req_file:- The path to the requirements.txt file.
        # -q:- Quiet mode, reduces output. Without -q it will show detailed installation logs. like- Downloading...  Installing...  Collecting...  Successfully installed...
        # python3 -m pip:- Run the pip module using the Python interpreter.
        # python3 -m pip install -r requirements.txt:- Install all dependencies listed in the requirements.txt file.
        # python3 -m pip install -r requirements.txt -q:- Install dependencies quietly, without verbose output.
        [sys.executable, "-m", "pip", "install", "-r", str(req_file), "-q"],
        # capture_output=True:- Command ke stdout aur stderr ko Python me capture (save) karta hai.
        # text=True:- Captured output ko bytes ki jagah normal string (str) me return karta hai.
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"  ❌ Install failed:\n{result.stderr}")
        sys.exit(1)
    print("  ✅ Dependencies installed\n")


# ─────────────────────────────────────────────
# STEP 3 — Tunnel provider selection
# ─────────────────────────────────────────────

def setup_tunnel() -> dict:
    print("📋 Step 3: Public URL / Tunnel setup... \n")
    print("  Claude.ai web se connect karne ke liye ek public HTTPS URL chahiye. \n")

    print("  NOTE: claude.ai web only accepts an HTTPS public URL.")
    print("        A localhost/local URL will NOT work in claude.ai.")
    print("        For Claude Code CLI (terminal), local will also work. \n")

    provider = ask_choice(
        "Which tunnel provider would you like to use?",
        [
            ("tailscale",   "Tailscale Funnel  — Free, stable URL, no domain needed (Recommended)"),
            ("ngrok",       "Ngrok             — Free static domain provided (1 per account)"),
            ("cloudflare",  "Cloudflare Tunnel — Free, stable, needs your own domain"),
            ("manual",      "Manual URL        — I already have a URL (any provider)"),
            ("cli_only",    "Claude Code CLI only — no claude.ai web, only using it in the terminal"),
        ],
    )
    print()

    if provider == "tailscale":
        return _setup_tailscale()
    if provider == "ngrok":
        return _setup_ngrok()
    if provider == "cloudflare":
        return _setup_cloudflare()
    if provider == "manual":
        return _setup_manual()
    # cli_only
    print("  ✅ Local only mode — http://localhost:8080/mcp")
    print("  ⚠ Claude Code CLI mein add karo (claude.ai web mein nahi chalega).\n")
    return {"tunnel_provider": "local_only"}


# ── Tailscale ──────────────────────────────

def _setup_tailscale() -> dict:
    print("  ── Tailscale Funnel Setup ──")

    # shutil.which("tailscale"):- tailscale kaha install hai ye check karta hai and path return karta hai, agar nahi hai to None return karega
    if not shutil.which("tailscale"):
        print("  tailscale not found. Please install:")
        print("    curl -fsSL https://tailscale.com/install.sh | sh")
        print("    sudo tailscale up")
        print()
        input("  After install press the enter... ")

    print()
    print("  Funnel enable karo:")
    print("    sudo tailscale funnel reset")
    print("    sudo tailscale funnel 8080")
    print()
    print("  URL kuch aisa dikhega:")
    print("    https://your-machine-name.tail1234.ts.net/")
    print()
    input("  After URL is available, press enter... ")

    url = ask("  Your Tailscale URL (e.g. https://suv.tail8f8b29.ts.net)")
    url = _normalize_url(url)
    print(f"\n  ✅ Saved: {url}\n")
    return {"tunnel_provider": "tailscale", "tunnel_url": url}


# ── Ngrok ──────────────────────────────────

def _setup_ngrok() -> dict:
    print("  ── Ngrok Setup ──")

    if not shutil.which("ngrok"):
        print("  ngrok nahi mila. Install karo:")
        system = platform.system().lower()
        if system == "linux":
            print("    curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc")
            print("    echo 'deb https://ngrok-agent.s3.amazonaws.com buster main' | sudo tee /etc/apt/sources.list.d/ngrok.list")
            print("    sudo apt update && sudo apt install ngrok")
        elif system == "darwin":
            print("    brew install ngrok/ngrok/ngrok")
        else:
            print("    https://ngrok.com/download se download karo")
        print()
        input("  Install karke Enter dabao... ")

    print()
    print("  Static domain ke liye:")
    print("  1. https://ngrok.com par free account banao")
    print("  2. Dashboard → Domains → 'New Domain' — ek free static domain milega")
    print("  3. Terminal mein:")
    print("     ngrok config add-authtoken <YOUR_TOKEN>")
    print("     ngrok http --domain=your-domain.ngrok-free.app 8080")
    print()
    input("  Jab domain ready ho, Enter dabao... ")

    domain = ask("  Ngrok domain (e.g. your-domain.ngrok-free.app)")
    authtoken = ask("  Ngrok auth token (dashboard mein milega)")
    url = _normalize_url(domain)

    # Save authtoken to ngrok config
    if authtoken:
        subprocess.run(["ngrok", "config", "add-authtoken", authtoken],
                       capture_output=True)

    print(f"\n  ✅ Saved: {url}\n")
    return {
        "tunnel_provider": "ngrok",
        "tunnel_url": url,
        "ngrok_domain": domain.replace("https://", "").replace("http://", ""),
        "ngrok_authtoken": authtoken,
    }


# ── Cloudflare ─────────────────────────────

def _setup_cloudflare() -> dict:
    print("  ── Cloudflare Tunnel Setup ──")

    if not shutil.which("cloudflared"):
        print("  cloudflared nahi mila. Install karo:")
        _install_cloudflared()

    print()
    print("  1. https://cloudflare.com par free account banao")
    print("  2. Apna domain Cloudflare mein add karo")
    print("  3. Terminal mein:")
    print("     cloudflared login")
    print("     cloudflared tunnel create my-mcp")
    print("     cloudflared tunnel route dns my-mcp mcp.yourdomain.com")
    print()
    input("  Jab setup ho jaye, Enter dabao... ")

    tunnel_name = ask("  Tunnel naam (e.g. my-mcp)", "my-mcp")
    tunnel_url = ask("  Tunnel URL (e.g. mcp.yourdomain.com)")
    tunnel_url = _normalize_url(tunnel_url)

    print(f"\n  ✅ Saved: {tunnel_url}\n")
    return {
        "tunnel_provider": "cloudflare",
        "tunnel_url": tunnel_url,
        "tunnel_name": tunnel_name,
    }


def _install_cloudflared():
    system = platform.system().lower()
    machine = platform.machine().lower()
    urls = {
        ("linux", "x86_64"):  "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64",
        ("linux", "aarch64"): "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64",
        ("darwin", "x86_64"): "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-amd64.tgz",
        ("darwin", "arm64"):  "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-arm64.tgz",
    }
    url = urls.get((system, machine))
    if not url:
        print(f"  ❌ Auto-install nahi ({system}/{machine}). Manual: https://developers.cloudflare.com/cloudflared/get-started/")
        return
    dest = CONFIG_DIR / "cloudflared"
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    print("  Downloading cloudflared...")
    result = subprocess.run(["curl", "-L", "-o", str(dest), url], capture_output=True)
    if result.returncode == 0:
        dest.chmod(0o755)
        os.environ["PATH"] = str(CONFIG_DIR) + ":" + os.environ.get("PATH", "")
        print(f"  ✅ cloudflared installed: {dest}")
    else:
        print("  ❌ Download failed. Manual install karo.")


# ── Manual ─────────────────────────────────

def _setup_manual() -> dict:
    print("  ── Manual URL Setup ──")
    print()
    print("  Agar aapke paas pehle se koi public HTTPS URL hai")
    print("  (kisi bhi provider ka — bore.pub, localtunnel, etc.)")
    print()
    url = ask("  Aapka public URL (https://...)")
    url = _normalize_url(url)
    print(f"\n  ✅ Saved: {url}\n")
    return {"tunnel_provider": "manual", "tunnel_url": url}


def _normalize_url(url: str) -> str:
    url = url.strip().rstrip("/")
    if url and not url.startswith("https://") and not url.startswith("http://"):
        url = "https://" + url
    return url


# ─────────────────────────────────────────────
# STEP 4 — Plugin / Framework selection
# ─────────────────────────────────────────────

ALL_PLUGINS = [
    ("frappe",        "Frappe / ERPNext    — Frappe bench, sites, DocTypes, API"),
    ("vue",           "Vue.js              — Vue 3, Vite, Nuxt"),
    ("react",         "React               — React, Next.js, Vite"),
    ("flutter",       "Flutter             — Dart, Android, iOS builds"),
    ("django",        "Django              — Python web framework"),
    ("fastapi",       "FastAPI             — Python async API"),
    ("flask",         "Flask               — Python micro-framework"),
    ("node",          "Node.js             — Express, npm scripts"),
    ("laravel",       "Laravel             — PHP framework"),
    ("docker",        "Docker              — Containers, compose, logs"),
    ("postgres",      "PostgreSQL          — DB queries, migrations"),
    ("mysql",         "MySQL / MariaDB     — DB queries, migrations"),
    ("mongodb",       "MongoDB             — Collections, queries"),
    ("aws",           "AWS                 — S3, Lambda, EC2 basics"),
    ("react_native",  "React Native        — Mobile apps, Expo"),
    ("android",       "Android             — Gradle, ADB, APK"),
    ("springboot",    "Spring Boot         — Java/Kotlin backend"),
    ("playwright",    "Playwright          — Browser automation/testing"),
    ("llm",           "LLM / AI tools      — OpenAI, HuggingFace, etc."),
    ("angular",       "Angular             — TypeScript SPA framework"),
    ("nuxt",          "Nuxt.js             — Vue-based SSR framework"),
    ("nextjs",        "Next.js             — React-based SSR framework"),
    ("rag",           "RAG / Vector DB     — Embeddings, FAISS, Chroma"),
    ("cloud",         "Cloud / DevOps      — GCP, Azure, Terraform basics"),
    ("vscode",        "VS Code             — Extensions, workspace settings"),
    ("generic",       "Generic             — Shell, git, file ops (always on)"),
]


def setup_plugins() -> dict:
    print("📋 Step 4: Frameworks / Plugins select karo...")
    print()
    print("  Jinpar aap kaam karte ho unhe select karo.")
    print("  (Baad mein wizard dobara chalake change kar sakte ho)")
    print()
    print("  Available plugins:")
    print()

    for i, (key, label) in enumerate(ALL_PLUGINS, 1):
        marker = "  [always on]" if key == "generic" else ""
        # {i:2}:- i ko minimum width 2 characters me print karega. kuchh aise
        #  1.
        #  2.
        #  3.
        # 10.
        # without {i:2} it will be like this
        # 1.
        # 2.
        # 3.
        # 10.
        print(f"  {i:2}. {label}{marker}")

    print()
    print("  Numbers enter karo (comma separated), e.g.: 1,2,4")
    print("  Ya 'all' type karo sab select karne ke liye")
    print()

    while True:
        raw = input("  Aapki choice: ").strip().lower()
        if not raw:
            print("  ❌ Kuch to select karo. Enter dabao.")
            # niche ka code abhi execute nahi hoga, dobara loop start hoga jabtak user valid input nahi deta
            continue

        if raw == "all":
            selected = [key for key, _ in ALL_PLUGINS]
            break

        # replace(" ", ",") se har space comma banta hai, isliye "1, 2, 3" -> "1,,2,,3" (do-do comma).
        # split(",") se beech me khaali "" aati hain, par 'if p.strip()' unhe hata deta hai — output sahi rehta hai.
        parts = [p.strip() for p in raw.replace(" ", ",").split(",") if p.strip()]
        valid = []
        invalid = []
        for p in parts:
            if p.isdigit() and 1 <= int(p) <= len(ALL_PLUGINS):
                valid.append(ALL_PLUGINS[int(p) - 1][0])
            else:
                invalid.append(p)

        if invalid:
            print(f"  ❌ Invalid: {', '.join(invalid)} — sirf numbers 1-{len(ALL_PLUGINS)} enter karo.")
            continue

        # generic always included
        if "generic" not in valid:
            valid.append("generic")

        selected = valid
        break

    print()
    print("  Selected plugins:")
    # Python me loop apna alag scope nahi banata. if, for, while blocks ke andar bani variables usi function ke scope ki hoti hain — block ke bahar bhi zinda rehti hain. (Ye C/Java/JS {} block-scope se alag hai; Python me sirf function naya scope banata hai, loop ya if else me nahi.)
    for key in selected:
        # (l for k, l in ALL_PLUGINS if k == key):- ye ek generator expression hai jo ALL_PLUGINS me se key match hone par label return karega.
        # next(generator, default):- ye generator se pehla value return karega, agar generator khali hai to default return karega. Yaha default 2nd argument(key) hai.
        label = next((l for k, l in ALL_PLUGINS if k == key), key)
        print(f"    ✅ {label}")
    print()

    return {"active_plugins": selected}


# ─────────────────────────────────────────────
# STEP 5 — Project Registry
# ─────────────────────────────────────────────

def setup_projects() -> dict:
    print("📋 Step 5: Register your project...")
    print()
    print("  When your say AI 'Now work on vue'")
    print("  Then it will switch directly to that folder.")
    print()
    print("  Specify a name and path for each project.")
    print("  (Name short rakho — e.g. 'frappe', 'vue', 'app')")
    print()

    projects = []
    while True:
        print(f"  ── Project {len(projects) + 1} ──")
        path = ask("  Project path (Enter = skip/done)").strip()
        if not path:
            if not projects:
                print("  ⚠ Koi project register nahi kiya. Baad mein `register_project` tool se kar sakte ho.\n")
            break

        # .expanduser():- suppose my home directory /home/kk/ and jab mai terminal me cd ~ type + enter karta hu to home directory me chala jata hu. yaani ~ hi /home/kk/ hai. and jab mai .expanduser() use karta hu to ~ ko /home/kk/ me convert kar deta hai.
        # .resolve(): relative/uljhe hue path ko saaf-suthre absolute path me badalna, taaki registry me reliable path save ho. ex- /home/kk/projects/../vue → /home/kk/vue
        resolved = Path(path).expanduser().resolve()
        if not resolved.exists():
            print(f"  ❌ Path exist nahi karta: {resolved} — dobara try karo.\n")
            continue

        # Auto-detect framework
        from core.project_detector import detect_framework
        detected = detect_framework(str(resolved))
        detected_fw = detected[0]["framework"] if detected else "generic"

        default_name = resolved.name  # folder name as default
        name = ask(f"  Is project ka naam (detected: {detected_fw})", default_name).strip().lower()
        name = name.replace(" ", "_")

        projects.append({
            "name": name,
            "path": str(resolved),
            "framework": detected_fw,
        })
        print(f"  ✅ Registered: '{name}' → {resolved} ({detected_fw})\n")

        if not ask_yes_no("  Do you need to add more projects?", default=True):
            break

    if projects:
        print(f"\n  {len(projects)} project(s) registered:")
        for p in projects:
            print(f"    • {p['name']:15} → {p['path']}  [{p['framework']}]")
        print()

    return {"projects": projects}


# ─────────────────────────────────────────────
# STEP 6 — Email (optional)
# ─────────────────────────────────────────────

def setup_email() -> dict:
    print("📋 Step 6: Email setup (OTP ke liye, optional)...")
    print("  Email setup nahi karne par OTP terminal mein print hoga.")
    print()

    if not ask_yes_no("  Email se OTP chahiye?", default=False):
        print("  ⚠ OTP terminal mein dikhega — OK\n")
        return {}

    smtp_host = ask("  SMTP Host (e.g. smtp.gmail.com)", "smtp.gmail.com")
    smtp_port = ask("  SMTP Port", "587")
    from_email = ask("  Sender email (jo bhejega OTP)")
    password = ask("  Email password / App password")

    print()
    print("  OTP kis email par receive karna chahte ho?")
    print("  (Enter dabao same email rakhne ke liye)")
    to_email = ask("  Receiver email", from_email).strip() or from_email

    # Test connection
    print()
    print("  Email connection test kar raha hoon...")
    try:
        import smtplib
        with smtplib.SMTP(smtp_host, int(smtp_port)) as server:
            server.starttls()
            server.login(from_email, password)
        print("  ✅ Email connection successful!\n")
    except Exception as e:
        print(f"  ⚠ Email test failed: {e}")
        print("  OTP terminal mein print hoga as fallback.\n")

    cfg = {
        "smtp_host": smtp_host,
        "smtp_port": int(smtp_port),
        "from_email": from_email,
        "smtp_password": password,
    }
    if to_email != from_email:
        cfg["to_email"] = to_email

    return {"email": cfg}


# ─────────────────────────────────────────────
# Save + Final steps
# ─────────────────────────────────────────────

def save_config(config: dict):
    # .mkdir:- make directory. it's create a directory if it is does not already exist.
    # parents=True:- agar parent directory exist nahi karta to bhi create kar dega. ex. /home/kk/.universal-dev-mcp/config.json ke liye agar .universal-dev-mcp exist nahi karta to bhi create kar dega.
    # exist_ok=True:- agar directory already exist karta to bhi error nahi dega.
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def print_next_steps(config: dict):
    # config.get:- tunnel_url key ka value return karta hai agar nahi mila to default empty string return karega without raising KeyError.
    tunnel_url = config.get("tunnel_url", "")
    provider = config.get("tunnel_provider", "none")
    plugins = [p for p in config.get("active_plugins", []) if p != "generic"]

    print("\n" + "=" * 55)
    print("  ✅ SETUP COMPLETE!")
    print("=" * 55)
    print()
    print("  Server start karo:")
    print("    python3 main.py start --project /your/project/path")
    print()

    if provider == "tailscale":
        print("  Tunnel start karo (har baar):")
        print("    sudo tailscale funnel 8080")
        print()
    elif provider == "ngrok":
        domain = config.get("ngrok_domain", "your-domain.ngrok-free.app")
        print("  Tunnel start karo (har baar):")
        print(f"    ngrok http --domain={domain} 8080")
        print()
    elif provider == "cloudflare":
        name = config.get("tunnel_name", "my-mcp")
        print("  Tunnel start karo (har baar):")
        print(f"    cloudflared tunnel run {name}")
        print()

    if provider == "local_only":
        print("  Claude Code CLI mein add karo:")
        print("    claude mcp add universal-mcp http://localhost:8080/mcp")
        print()
        print("  ⚠ claude.ai web mein LOCAL URL kaam nahi karega.")
        print("     Web ke liye tunnel setup karo (wizard dobara chalao).")
    else:
        print("  Claude.ai web mein add karo:")
        print("    Settings → Integrations → Custom MCP")
        print()
        print("  Local URL:  http://localhost:8080/mcp")
    if tunnel_url:
        print(f"  Remote URL: {tunnel_url}/mcp")
    print()
    if plugins:
        print("  Active plugins: " + ", ".join(plugins))
        print()
    print("  ✅ Ek baar add karo — hamesha kaam karega!")
    print("=" * 55 + "\n")


def run():
    print_banner()
    check_python()
    install_requirements()

    config = {}
    tunnel_cfg = setup_tunnel()
    config.update(tunnel_cfg)

    plugin_cfg = setup_plugins()
    config.update(plugin_cfg)

    project_cfg = setup_projects()
    config.update(project_cfg)

    email_cfg = setup_email()
    config.update(email_cfg)

    config["default_port"] = 8080
    save_config(config)
    print_next_steps(config)


if __name__ == "__main__":
    run()
