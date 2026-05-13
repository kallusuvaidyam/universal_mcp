# Universal Dev MCP

Claude AI ko aapke kisi bhi project se directly connect karo — Frappe, Django, Next.js, Laravel, ya koi bhi framework.

## Features

- **Koi bhi project** — Django, Next.js, Laravel, React, Rust, Go, ya generic
- **Local + Remote** — localhost aur Cloudflare stable tunnel dono ek saath
- **Hybrid Detection** — auto-detect framework + Claude se confirm
- **15+ Universal Tools** — shell, file, git, logs, docker, tests, packages
- **Plugin System** — framework-specific tools (Frappe, Django, etc.)
- **Non-tech friendly** — ek wizard se poora setup

## Quick Start

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/universal-mcp
cd universal-mcp

# 2. One-time setup
python setup_wizard.py

# 3. Roz start karo
python main.py start --project /path/to/your/project
```

## Claude.ai Mein Add Karo

```
Settings → Integrations → Custom MCP → http://localhost:8080
```

## Frappe Users

Built-in Frappe plugin available hai. Config example ke liye `plugins/frappe/README.md` dekho.

## Available Tools

| Tool | Kya Karta Hai |
|------|--------------|
| `shell_run` | Koi bhi terminal command |
| `file_read` | File padhna |
| `file_write` | File likhna |
| `file_list` | Directory contents |
| `file_search` | Text search across files |
| `git_status` | Git status/log/diff |
| `git_commit` | Add + commit (+ optional push) |
| `env_read` | .env file (secrets masked) |
| `log_tail` | Log file ke last N lines |
| `port_check` | Running ports dekhna |
| `docker_ps` | Docker containers |
| `docker_logs` | Container logs |
| `test_run` | Tests (pytest/jest/phpunit auto-detect) |
| `package_install` | pip/npm/composer auto-detect |
| `project_context` | .mcp-config.json load |
| `memory_save/get` | Claude ke liye notes |
| `browser_*` | Playwright browser automation |
| `desktop_*` | Desktop GUI control |

## Detailed Setup

`SETUP.md` padho.
