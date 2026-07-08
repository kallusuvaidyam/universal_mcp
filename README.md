# Universal Dev MCP

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that gives Claude AI access to **your own** development environment — across any framework, any of your projects, from anywhere.

Connect Claude (via claude.ai web or Claude Code CLI) to your local machine and let it read files, run commands, manage Git, control browsers, switch between projects, and remember context across sessions.

> **Scope:** This is a **single-developer** tool. It is designed for one person driving their own machine. Run it on your own trusted network — do not treat the OTP gate as multi-user access control. See [Security Notes](#security-notes).

---

## What It Does

- **90+ built-in tools** — shell, file ops (edit/grep/tree/move), git (diff/branch/stash/pull), docker, background services, HTTP client, DB query, env, logs, ports, browser automation, desktop control
- **26 framework plugins** — Frappe is a full integration (bench, API, doctype control); the rest (Vue, React, Flutter, Django, Next.js, Laravel, and more) are lighter helpers that mostly build/test and locate framework files
- **Multi-project workflow** — register all *your* projects, switch by name ("ab Vue par kaam karo")
- **Persistent memory** — Claude remembers decisions, errors, and context across sessions (SQLite)
- **OTP gate** — a single-user token check on every tool call (one shared credential, not per-user accounts)
- **Public URL tunneling** — Tailscale, Ngrok, or Cloudflare for claude.ai web access
- **Framework auto-detection** — scans your project and detects framework automatically

---

## Requirements

- Python 3.10 or higher
- pip
- Git
- Docker (optional, for Frappe/container-based projects)
- A public tunnel tool for claude.ai web: [Tailscale](https://tailscale.com), [Ngrok](https://ngrok.com), or [Cloudflare](https://cloudflare.com)
- For **browser tools**: a Chromium download via `playwright install chromium` (see Step 2 below)
- For **desktop tools** (Linux): `xdotool` and a screenshot tool (`scrot` or ImageMagick), plus `python3-tk`

---

## Quick Start

### Step 1 — Clone the repo

```bash
git clone <repo-url> universal-mcp
cd universal-mcp
```

### Step 2 — Run the setup wizard

```bash
python setup_wizard.py
```

The wizard will guide you through (step by step):

1. Python version check
2. Install dependencies (`requirements.txt`)
3. Tunnel provider setup (Tailscale / Ngrok / Cloudflare / manual URL / CLI only)
4. Select framework plugins you need (Frappe, Vue, Flutter, etc.)
5. Register your projects (name + path — so you can switch by name later)
6. Optional email setup for OTP delivery

Setup creates `~/.universal-dev-mcp/config.json` — you never need to run it again unless you add a new project.

> **After setup — install the extras the wizard does not:**
> ```bash
> playwright install chromium              # required before any browser_* tool works
> pip install pillow                       # used by desktop screenshot tools
> # Linux desktop tools also need: sudo apt install xdotool scrot python3-tk
> ```
> Skip these if you don't use the browser/desktop tools.

### Step 3 — Start the server

```bash
python main.py start
```

Server starts on `http://localhost:8080`. You will see:

```
Local URL:  http://localhost:8080/mcp
Remote URL: https://your-tunnel-url.ts.net/mcp
```

### Step 4 — Start your tunnel (if using claude.ai web)

Run this in a separate terminal and keep it open:

| Provider   | Command                                                         |
|------------|-----------------------------------------------------------------|
| Tailscale  | `sudo tailscale funnel 8080`                                    |
| Ngrok      | `ngrok http --domain=your-domain.ngrok-free.app 8080`           |
| Cloudflare | `cloudflared tunnel run my-mcp`                                 |

> **Note:** claude.ai web only accepts HTTPS public URLs. `localhost` will be rejected. The tunnel must be running before you add the URL to claude.ai.

### Step 5 — Add to Claude

**Claude.ai web:**
1. Go to `claude.ai` → Settings → Integrations
2. Click **Add Custom MCP**
3. Enter: `https://your-tunnel-url/mcp`

**Claude Code CLI (local only):**
```bash
claude mcp add universal-mcp http://localhost:8080/mcp
```

---

## First Use — Authentication

Every tool call requires an OTP token. This is a **single-user gate** — one OTP identity for the whole server, not separate developer accounts. On first use:

1. Call `verify_session` tool with an empty code — this sends an OTP
2. If email is configured, check your inbox. Otherwise, the OTP prints in the server terminal
3. Call `verify_session` again with the 6-digit code
4. You receive a session token — pass it to all subsequent tool calls
5. The token expires after 2 hours of **inactivity** (each use refreshes it); restarting the server clears all sessions

---

## Folder Structure

```
universal-mcp/
│
├── main.py                   # CLI entry point — start, setup commands
├── server.py                 # MCP server core — 90+ tool definitions and dispatch
├── auth.py                   # OTP authentication and session management
├── config.py                 # Config file handling (~/.universal-dev-mcp/)
├── tunnel.py                 # Public URL tunnel management (CF, Tailscale, Ngrok)
├── setup_wizard.py           # Interactive one-time setup wizard
├── requirements.txt          # Python dependencies
├── .mcp-config.example.json  # Per-project config template
│
├── core/                     # Universal tool implementations
│   ├── project_detector.py   # Framework auto-detection via file signatures
│   ├── project_context.py    # Config loader + framework switch detection
│   ├── memory_manager.py     # SQLite memory (4 types: project, decision, debug, semantic)
│   ├── agent_planner.py      # Structured plan generator for Claude
│   ├── browser_automation.py # Playwright browser automation
│   ├── desktop_control.py    # Desktop GUI automation (xdotool / XTEST + Pillow)
│   ├── shell_executor.py     # Shell command runner (project cwd; best-effort blocklist)
│   ├── file_manager.py       # Safe project-jailed file operations
│   ├── git_ops.py            # Git status, log, diff, commit, push
│   ├── env_manager.py        # .env reading with secret masking
│   ├── log_reader.py         # Log file tailing and grep
│   ├── docker_ops.py         # Docker container management
│   ├── test_runner.py        # Auto-detect and run tests
│   ├── package_manager.py    # pip / npm / composer install
│   └── port_manager.py       # Port availability check
│
└── plugins/                  # Framework-specific tool extensions
    ├── __init__.py           # Plugin loader — maps names to modules
    ├── shared.py             # Shared helpers (run_command, collect_files)
    ├── frappe/               # Frappe/ERPNext tools (9 files)
    ├── vue/                  # Vue.js tools
    ├── flutter/              # Flutter mobile tools
    ├── react/                # React tools
    ├── django/               # Django tools
    ├── nextjs/               # Next.js tools
    ├── laravel/              # Laravel PHP tools
    ├── generic/              # Fallback tools (always loaded)
    └── ...                   # 26 frameworks total (most are lightweight file-discovery helpers)
```

---

## Global Config Location

Everything is stored in `~/.universal-dev-mcp/`:

| File              | Purpose                                            |
|-------------------|----------------------------------------------------|
| `config.json`     | Global settings (tunnel, email, plugins, projects) |
| `mcp-config.json` | Default framework config overrides                 |
| `memory.db`       | SQLite database for Claude's persistent memory     |

---

## Per-Project Config

Create `.mcp-config.json` in your project root for project-specific settings:

```json
{
  "framework": "django",
  "language": "python",
  "db": "postgresql",
  "env_file": ".env",
  "django": {
    "run_command": "python manage.py runserver",
    "test_command": "pytest"
  }
}
```

See `.mcp-config.example.json` for all options. For Frappe multi-bench config, see `plugins/frappe/README.md`.

---

## Available Tools

### Core Tools (always available)

| Tool                   | What it does                                        |
|------------------------|-----------------------------------------------------|
| `verify_session`       | OTP login — must call first                         |
| `switch_project`       | Switch to a registered project by name              |
| `list_projects`        | List all registered projects with active marker     |
| `register_project`     | Add a new project to registry at runtime            |
| `project_context`      | Load current project framework and config           |
| `confirm_framework`    | Save framework to `.mcp-config.json`                |
| `shell_run`            | Run any terminal command in project directory       |
| `file_read`            | Read a file (50KB limit)                            |
| `file_write`           | Create or overwrite a file                          |
| `file_list`            | List directory contents                             |
| `file_search`          | Search text across project files                    |
| `git_status`           | Git status / log / diff / branch                    |
| `git_commit`           | Stage all + commit (optional push)                  |
| `env_read`             | Read .env file (secrets masked by key name — see Security Notes) |
| `log_tail`             | Tail or grep log files                              |
| `port_check`           | Check which ports are listening                     |
| `docker_ps`            | List Docker containers                              |
| `docker_logs`          | View container logs                                 |
| `test_run`             | Auto-detect and run tests (pytest/jest/phpunit)     |
| `package_install`      | Install package (pip/npm/composer auto-detected)    |
| `generate_plan`        | Generate a structured action plan                   |
| `memory_save/get/list` | Simple key-value memory per project                 |
| `project_memory_*`     | Per-project notes (scoped by a `user_id` you pass)  |
| `decision_memory_*`    | Store and search past decisions                     |
| `debug_memory_*`       | Track errors and resolutions                        |
| `semantic_memory_*`    | Tagged knowledge snippets                           |
| `browser_launch`       | Start Playwright browser                            |
| `browser_navigate`     | Open URL                                            |
| `browser_click`        | Click element by selector                           |
| `browser_type`         | Type text into input                                |
| `browser_screenshot`   | Capture browser screenshot                          |
| `desktop_screenshot`   | Capture desktop screen                              |
| `desktop_open_app`     | Open an application                                 |
| `desktop_click`        | Click at screen coordinates                         |
| `desktop_type`         | Type text on desktop                                |

### Daily-use tools

| Tool | What it does |
|------|--------------|
| `file_edit` | Replace an exact, unique substring in a file (no full rewrite) |
| `file_grep` | Search text, returns `file:line:content` (with optional context) |
| `file_read_lines` | Read a file with line numbers + offset/limit range |
| `file_append` | Append text to a file (creates if missing) |
| `file_move` / `file_delete` / `file_mkdir` | Move/rename, delete (recursive opt-in), create directory |
| `file_tree` | Recursive directory tree (skips node_modules/.git/etc.) |
| `git_diff` | Working-tree diff, optionally one file |
| `git_log` / `git_branch` / `git_checkout` | History / list branches / switch branch |
| `git_branch_create` | Create + switch to a new branch |
| `git_add` / `git_stash` / `git_pull` / `git_push` | Stage paths / stash push-pop-list-drop / pull / push |
| `git_restore` / `git_show_file` | Discard-or-unstage a file / view a file at a revision |
| `service_run` | Start a long-running command in the background (dev server, `bench start`) |
| `service_logs` | Tail a service's output, or list all tracked services |
| `service_stop` / `service_restart` | Stop / restart a background service |
| `http_request` | HTTP client for testing local endpoints |
| `db_query` | Read-only SQL query (writes need `confirm=True`) |
| `docker_exec` | Run a command inside a container |
| `docker_compose_up` / `docker_compose_down` / `docker_restart` | Compose stack up / down (confirm) / restart one container |
| `port_kill` | Kill the process bound to a port |
| `env_get` | Read one key from `.env` |
| `log_grep` | Grep a log file for a pattern |
| `package_list` / `package_remove` | List / uninstall dependencies |
| `scripts_list` / `script_run` | List / run a `package.json` script |
| `typecheck` | Run `tsc --noEmit` for TypeScript projects |

### Plugin Tools (loaded based on selected frameworks)

| Framework | Added Tools                                                                                                                                       |
|-----------|---------------------------------------------------------------------------------------------------------------------------------------------------|
| Frappe    | `frappe_api_call`, `frappe_execute`, `frappe_bench_start`, `frappe_bench_migrate`, `frappe_bench_restart`, `frappe_bench_backup`, `frappe_bench_build`, `frappe_list_sites`, `frappe_get_logs`, `frappe_create_doctype` |
| Vue       | `vue_build`, `vue_test`, `vue_lint`, `vue_list_views`                                                                                             |
| Flutter   | `flutter_pub_get`, `flutter_test`, `flutter_analyze`, `flutter_build_apk`, `flutter_list_screens`                                                |
| Django    | `django_migrate`, `django_makemigrations`, `django_shell`, `django_check`, `django_collectstatic`                                                 |
| React     | `react_build`, `react_test`, `react_list_components`                                                                                              |
| Generic   | `generic_run_dev`, `generic_readme`                                                                                                               |

> The frameworks above have curated tools. The remaining plugins (e.g. `aws`, `mongodb`, `springboot`, `cloud`, `angular`, `node`) mostly expose file-discovery helpers — they locate config/source files rather than deeply drive the framework. `generic` is always loaded alongside whichever framework is active.

---

## Switching Between Projects

Register projects during setup wizard, or at runtime:

```
User: "ab Vue par kaam karo"
AI calls: switch_project(name="vue")

User: "frappe mein kaam karo"
AI calls: switch_project(name="frappe")

User: "konse projects hain?"
AI calls: list_projects()
```

Add a new project without re-running wizard:

```
AI calls: register_project(name="myapi", project_path="/workspace/my-fastapi-app")
```

---

## Adding a New Framework Plugin

1. Create `plugins/yourframework/` directory with `__init__.py` and `yourframework_ops.py`

2. In `yourframework_ops.py`:

```python
import subprocess

def your_tool(project_path: str, some_arg: str = "") -> str:
    result = subprocess.run(
        ["your-cli", some_arg], cwd=project_path,
        capture_output=True, text=True, timeout=60
    )
    return result.stdout or result.stderr

TOOLS = {
    "your_tool": {"fn": your_tool, "description": "What this tool does"},
}
```

3. Register in `plugins/__init__.py` `PLUGIN_MAP`:

```python
"yourframework": "plugins.yourframework",
```

4. Add to `setup_wizard.py` `ALL_PLUGINS` list

---

## Troubleshooting

**"Couldn't reach the MCP server" in claude.ai**
- Verify the MCP server is running: `python main.py start`
- Verify the tunnel is running in a separate terminal
- Make sure the URL ends with `/mcp`: `https://your-url.ts.net/mcp`
- `localhost` URLs are always rejected by claude.ai web

**OTP not received by email**
- Check `smtp_password` in `~/.universal-dev-mcp/config.json`
- Gmail requires an App Password (not your account password)
- As fallback, the OTP always prints in the server terminal

**Bench not running / Frappe site not accessible**
- Check Docker containers: `docker ps`
- Ensure MariaDB and Redis containers are running
- Set auto-restart: `docker update --restart=unless-stopped <container-name>`
- Start bench inside container: `docker exec <container> bash -lc "nohup bench start > /tmp/bench.log 2>&1 &"`

**Framework not detected correctly**
- Run `project_context` tool — Claude will scan and suggest
- Confirm with `confirm_framework(framework="vue")` to save `.mcp-config.json`

**Plugin tools not showing up**
- Check `active_plugins` in `~/.universal-dev-mcp/config.json`
- Re-run setup wizard to add missing plugins: `python setup_wizard.py`

**Session expired**
- Tokens expire after 2 hours of inactivity — call `verify_session` again to renew

**`browser_launch` fails / "Executable doesn't exist"**
- Run `playwright install chromium` once (the setup wizard does not do this)

**`desktop_*` tools fail on Linux**
- Install `xdotool`, `scrot` (or ImageMagick), and `python3-tk`; ensure `pillow` is installed

---

## Security Notes

**Read this before exposing the server.** This is a single-developer tool. Treat a running server as *"whoever holds the token has a shell on my machine."*

- **`shell_run` is effectively full shell access — not a sandbox.** It runs your command with `shell=True` in the project directory. The built-in blocklist catches only a few exact patterns (`rm -rf /`, `mkfs`, `reboot`, …) and is trivially bypassed (`rm -fr /`, `find / -delete`, `bash -c '…'`). Do **not** rely on it as a safety boundary.
- **One shared credential.** There is a single OTP identity for the whole server; anyone with the OTP (which prints to the server terminal) gets the same full access. `developer_name` is just a label.
- **File tools are jailed** to the project directory — `../` and absolute-path traversal are blocked. But `shell_run` is **not** jailed and can read/write anywhere your user can.
- **`.env` masking is partial.** `env_read` masks values whose *key name* looks sensitive. It does **not** cover unusual key names, and `file_read(".env")` / `shell_run("cat .env")` return everything unmasked.
- **The server binds `127.0.0.1`** — it is only reachable remotely through the tunnel you start. Only run the tunnel on a network you trust, and stop it when you're done.
- Keep `"require_auth": true`. Set `false` only on a fully trusted, non-exposed local setup.

---

## License

MIT
