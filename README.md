# Universal Dev MCP

A universal [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that gives Claude AI full access to your development environment — across any framework, any project, from anywhere.

Connect Claude (via claude.ai web or Claude Code CLI) to your local machine and let it read files, run commands, manage Git, control browsers, switch between projects, and remember context across sessions.

---

## What It Does

- **40+ built-in tools** — shell, file ops, git, docker, env, logs, ports, browser automation, desktop control
- **30+ framework plugins** — Frappe, Vue, React, Flutter, Django, Next.js, Laravel, and more
- **Multi-project support** — register all your projects, switch by name ("ab Vue par kaam karo")
- **Persistent memory** — Claude remembers decisions, errors, and context across sessions (SQLite)
- **OTP authentication** — secure token-based access; all tool calls are authenticated
- **Public URL tunneling** — Tailscale, Ngrok, or Cloudflare for claude.ai web access
- **Framework auto-detection** — scans your project and detects framework automatically

---

## Requirements

- Python 3.10 or higher
- pip
- Git
- Docker (optional, for Frappe/container-based projects)
- A public tunnel tool for claude.ai web: [Tailscale](https://tailscale.com), [Ngrok](https://ngrok.com), or [Cloudflare](https://cloudflare.com)

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

Every tool call requires an OTP token. On first use:

1. Call `verify_session` tool with an empty code — this sends an OTP
2. If email is configured, check your inbox. Otherwise, the OTP prints in the server terminal
3. Call `verify_session` again with the 6-digit code
4. You receive a session token — pass it to all subsequent tool calls
5. Token is valid for 2 hours

---

## Folder Structure

```
universal-mcp/
│
├── main.py                   # CLI entry point — start, setup commands
├── server.py                 # MCP server core — 40+ tool definitions and dispatch
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
│   ├── desktop_control.py    # Desktop GUI automation (PyAutoGUI + xdotool)
│   ├── shell_executor.py     # Sandboxed shell command runner
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
    └── ...                   # 22+ more frameworks
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
| `env_read`             | Read .env file (secrets masked)                     |
| `log_tail`             | Tail or grep log files                              |
| `port_check`           | Check which ports are listening                     |
| `docker_ps`            | List Docker containers                              |
| `docker_logs`          | View container logs                                 |
| `test_run`             | Auto-detect and run tests (pytest/jest/phpunit)     |
| `package_install`      | Install package (pip/npm/composer auto-detected)    |
| `generate_plan`        | Generate a structured action plan                   |
| `memory_save/get/list` | Simple key-value memory per project                 |
| `project_memory_*`     | User-scoped project notes                           |
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

### Plugin Tools (loaded based on selected frameworks)

| Framework | Added Tools                                                                                                                                       |
|-----------|---------------------------------------------------------------------------------------------------------------------------------------------------|
| Frappe    | `frappe_api_call`, `frappe_execute`, `frappe_bench_start`, `frappe_bench_migrate`, `frappe_bench_restart`, `frappe_bench_backup`, `frappe_bench_build`, `frappe_list_sites`, `frappe_get_logs`, `frappe_create_doctype` |
| Vue       | `vue_build`, `vue_test`, `vue_lint`, `vue_list_views`                                                                                             |
| Flutter   | `flutter_pub_get`, `flutter_test`, `flutter_analyze`, `flutter_build_apk`, `flutter_list_screens`                                                |
| Django    | `django_migrate`, `django_makemigrations`, `django_shell`, `django_check`, `django_collectstatic`                                                 |
| React     | `react_build`, `react_test`, `react_list_components`                                                                                              |
| Generic   | `generic_run_dev`, `generic_readme`                                                                                                               |

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
- Tokens expire after 2 hours — call `verify_session` again to renew

---

## Security Notes

- All tool calls require a valid OTP session token
- `shell_run` blocks dangerous commands (`rm -rf /`, `mkfs`, `dd`, `reboot`, etc.)
- File operations are jailed to the project directory — no path traversal
- `.env` secrets are automatically masked in `env_read` output
- Set `"require_auth": false` in global config only on fully trusted local networks

---

## License

MIT
