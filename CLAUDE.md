# CLAUDE.md — AI Assistant Instructions for Universal Dev MCP

Read this file completely before making any changes to this project.

---

## Project Purpose

Universal Dev MCP is a **Model Context Protocol (MCP) server** written in Python. It exposes 40+ tools to Claude AI — allowing Claude to interact with any developer's local machine: read/write files, run shell commands, manage Git, control browsers, switch between projects, and persist memory across sessions.

It is framework-agnostic by design, extended via a **plugin system** that adds framework-specific tools (Frappe, Vue, Flutter, Django, etc.) based on user configuration.

---

## Critical Rules — Read Before Any Edit

1. **Analyze before editing.** Always read the relevant file(s) before modifying. Understand what a function does, what calls it, and what it returns.
2. **Do not refactor unless explicitly asked.** The codebase follows established patterns. Renaming, restructuring, or abstracting existing code without a request will break callers.
3. **Do not add extra features.** If the task is to fix a bug, fix only that bug. Do not add logging, error handling, or fallbacks that were not requested.
4. **Follow existing patterns exactly.** Every plugin follows the same TOOLS dict pattern. Every core module returns strings. Every tool handler follows the same dispatch pattern. Match it.
5. **Do not modify `server.py`'s `ALL_TOOLS` list without also adding the handler.** Missing handlers cause `Unknown tool` errors at runtime.
6. **Do not change auth flow.** `auth.py` is security-critical. Changing OTP logic, session expiry, or the `_check_auth()` call order will break all tool calls.
7. **Do not break the plugin loader.** `plugins/__init__.py` PLUGIN_MAP must stay consistent with actual module paths. A typo here silently disables a framework.

---

## Architecture Overview

```
claude.ai / Claude Code CLI
         │
         │ MCP (HTTP/SSE over HTTPS tunnel)
         ▼
    server.py  ←── ALL entry point for tool calls
         │
         ├── auth.py           OTP session check (every tool call)
         ├── config.py         Read ~/.universal-dev-mcp/config.json
         │
         ├── core/*            Universal tool implementations
         │     ├── shell_executor.py
         │     ├── file_manager.py
         │     ├── git_ops.py
         │     ├── browser_automation.py
         │     ├── desktop_control.py
         │     ├── memory_manager.py
         │     ├── project_context.py  ← framework switching logic lives here
         │     ├── project_detector.py ← framework auto-detection
         │     └── ...
         │
         └── plugins/*         Framework-specific tools (loaded dynamically)
               ├── __init__.py         plugin loader
               ├── frappe/             frappe tools
               ├── vue/                vue tools
               └── ...
```

**Request lifecycle:**
1. Tool call arrives at `server.call_tool(name, arguments)`
2. `_check_auth(arguments)` — validates session token (fails immediately if invalid)
3. `pp = ACTIVE_PROJECT_PATH` — current active project path (mutable via `switch_project`)
4. Dispatch to the correct handler (core tool or plugin tool)
5. Plugin tools: `_call_plugin_tool(name, arguments, pp)` — auto-injects `project_path`

---

## Key Files and Their Responsibilities

### `server.py`
The only file that defines and dispatches MCP tools. Contains:
- `ALL_TOOLS` — list of `types.Tool` definitions (JSON schema for each tool)
- `call_tool()` — async dispatcher for every tool call
- `_project_frameworks()` — reads `active_plugins` from global config
- `_active_plugin_tools()` — loads and merges plugin TOOLS dicts
- `_call_plugin_tool()` — invokes plugin functions with auto-injected `project_path`
- `ACTIVE_PROJECT_PATH` — global mutable, changed only by `switch_project` tool
- `_build_app()` — Starlette ASGI app with `/mcp` route (Streamable HTTP)

**When adding a new tool:**
1. Add `types.Tool(...)` entry to `ALL_TOOLS`
2. Add `elif name == "your_tool":` handler in `call_tool()`
3. Import the implementing function at the top if it's a new module

### `auth.py`
OTP-based stateless authentication. Key behavior:
- `_pending_otps`: in-memory dict — OTP expires in 5 minutes
- `_sessions`: in-memory dict — session token expires in 2 hours
- `send_otp()` sends via SMTP if configured, else prints to console
- `auth_required()` returns `None` if valid, or an error string if not

**Do not change:** Session expiry, OTP generation, or the `_check_auth()` call in `server.py`. Auth state is in-memory and resets on server restart.

### `config.py`
Two config layers:
- **Global config** (`~/.universal-dev-mcp/config.json`): tunnel settings, email, `active_plugins`, `projects` registry
- **Project config** (`.mcp-config.json` in project root): framework, db, run_command, etc.

Config merging rule: project config wins over global config. Use `load_project_config(path)` to get the merged result. Never read the JSON files directly in other modules — always go through `config.py`.

### `core/project_context.py`
Handles framework detection and project context loading.
- `get_project_context(path)` — returns existing config or triggers detection message
- `check_framework_switch(path)` — compares saved config vs detected framework; returns warning string or `None`. Has 60-second cache to avoid repeated disk scans.
- `confirm_framework(path, framework)` — saves `.mcp-config.json`

### `core/project_detector.py`
Framework detection via `SIGNATURES` array. Each signature has:
- `framework`: name
- `signals`: list of `{path, is_dir, score, contains?}` entries
- `threshold`: minimum score to count as detected

`detect_framework(path)` returns list sorted by confidence. Add new frameworks here by adding to `SIGNATURES`.

### `core/memory_manager.py`
SQLite database at `~/.universal-dev-mcp/memory.db`. Four memory types:
- `project_memory` — simple key-value notes per project
- `decision_memory` — decisions with keyword-based search
- `debug_memory` — error tracking scoped by issue
- `semantic_memory` — tagged knowledge snippets

All functions take `project_path` as the scope key. Memory persists across server restarts.

### `core/browser_automation.py`
Playwright Chromium automation. Important constraints:
- Global `_lock` — only one browser operation at a time (thread-safe)
- Sessions saved to `/tmp/universal_mcp_sessions/browser_state.json`
- All functions return either a string result or a base64 image dict `{"_image": True, "data": ...}`
- Image returns are handled specially in `server.py`'s `r()` helper

### `plugins/__init__.py`
The plugin loader. `PLUGIN_MAP` maps framework name strings to module paths:
```python
"vue": "plugins.vue",
"frappe": "plugins.frappe",
```

`load_plugin_tools(framework)` always merges generic tools + framework tools. Returns `{tool_name: {fn, description}}`.

---

## Plugin System — Pattern to Follow

Every plugin must have exactly this structure:

```
plugins/
└── yourframework/
    ├── __init__.py       # exports TOOLS
    └── yourframework_ops.py   # implements TOOLS dict
```

`__init__.py`:
```python
from .yourframework_ops import TOOLS
__all__ = ["TOOLS"]
```

`yourframework_ops.py`:
```python
import subprocess
from plugins.shared import run_command  # use shared helpers when possible

def tool_name(project_path: str, arg: str = "") -> str:
    # Always use project_path as cwd
    # Always return a string (not dict, not None)
    # Catch exceptions and return error string
    try:
        result = subprocess.run(["cmd", arg], cwd=project_path,
                                capture_output=True, text=True, timeout=60)
        return result.stdout or result.stderr or "Done."
    except Exception as e:
        return f"Error: {e}"

TOOLS = {
    "tool_name": {"fn": tool_name, "description": "Short description for Claude"},
}
```

**Rules:**
- Function signature: first param is always `project_path: str`, rest are keyword args with defaults
- Return type: always `str` — never dict, never None (plugin system expects strings)
- `project_path` is auto-injected by `_call_plugin_tool()` — do not expose it to Claude in the tool schema
- Use `plugins/shared.py` helpers (`run_command`, `run_package_script`, `collect_files`) instead of duplicating subprocess logic
- Add to `plugins/__init__.py` PLUGIN_MAP and `setup_wizard.py` ALL_PLUGINS

---

## Naming Conventions

| Thing | Convention | Example |
|-------|-----------|---------|
| Tool names (MCP) | `snake_case` | `frappe_bench_start` |
| Plugin function names | `snake_case`, match tool name | `frappe_bench_start(project_path, ...)` |
| Plugin module files | `{framework}_ops.py` | `vue_ops.py` |
| Plugin directories | lowercase framework name | `plugins/vue/` |
| Config keys | `snake_case` | `active_plugins`, `tunnel_url` |
| Core modules | descriptive noun | `file_manager.py`, `git_ops.py` |

---

## Config Schema Reference

### `~/.universal-dev-mcp/config.json` (global)

```json
{
  "tunnel_provider": "tailscale",
  "tunnel_url": "https://suv.tail8f8b29.ts.net",
  "active_plugins": ["frappe", "vue", "flutter", "generic"],
  "projects": [
    {"name": "frappe", "path": "/workspace/erp-bench", "framework": "frappe"},
    {"name": "vue",    "path": "/workspace/my-vue-app", "framework": "vue"}
  ],
  "default_port": 8080,
  "require_auth": true,
  "email": {
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "from_email": "you@gmail.com",
    "smtp_password": "app-password"
  }
}
```

### `.mcp-config.json` (per-project, in project root)

```json
{
  "framework": "frappe",
  "project_path": "/workspace/erp-bench",
  "detected_by": "universal-dev-mcp",
  "frappe": {
    "bench_id": "erp-bench",
    "site": "mysite.localhost",
    "bench_path": "/workspace/erp-bench",
    "benches": [
      {
        "id": "erp-bench",
        "path": "/workspace/erp-bench",
        "docker_container": "devcontainer_frappe_1",
        "sites": {
          "mysite.localhost": {
            "api_key": "...",
            "api_secret": "...",
            "port": 8000
          }
        }
      }
    ]
  }
}
```

---

## Multi-Project Switching — How It Works

`ACTIVE_PROJECT_PATH` is a global variable in `server.py` initialized to `PROJECT_PATH` (set at startup).

The `switch_project` tool:
1. Takes `name` (looks up in `projects` registry in global config) or `project_path` directly
2. Updates `ACTIVE_PROJECT_PATH`
3. Calls `project_context.get_project_context(new_path)` for confirmation

All subsequent tool calls use `pp = ACTIVE_PROJECT_PATH`. This means switching is session-wide (per server process) but not persistent across server restarts.

**Framework switch warning:** `check_framework_switch(pp)` runs before every plugin tool call. If saved `.mcp-config.json` framework differs from detected framework, a warning is prepended to the result.

---

## Tool Dispatch Pattern

```python
# In server.py call_tool():

elif name == "your_tool":
    return r(module.your_function(pp, arguments["required_arg"], arguments.get("optional_arg", "")))
```

- `r()` wraps the result as `TextContent` or `ImageContent`
- `pp` = `ACTIVE_PROJECT_PATH` — always pass as first positional arg for core tools
- Plugin tools get `project_path` auto-injected via `_call_plugin_tool()` — don't pass manually
- Wrap in `try/except` only at the outer level — individual modules handle their own errors

---

## Framework Detection — Adding New Frameworks

Add to `SIGNATURES` in `core/project_detector.py`:

```python
{
    "framework": "yourframework",
    "signals": [
        {"path": "distinctive-file.json", "is_dir": False, "score": 50, "contains": '"yourframework"'},
        {"path": "distinctive-dir",       "is_dir": True,  "score": 30},
    ],
    "threshold": 50,
},
```

Score guidelines: unique config files = 50, source dirs = 20-30, common files with content check = 30-40. Threshold should require at least one strong signal.

---

## Memory Usage Guidelines for Claude

Use memory tools to retain context across sessions:

| Situation | Use |
|-----------|-----|
| User confirmed a framework or config | `project_memory_set` |
| A decision was made (e.g., "use port 8002") | `decision_memory_add` |
| A bug was fixed and root cause found | `debug_memory_add` |
| A useful pattern was found in the codebase | `semantic_memory_add` |
| Starting a new task | `decision_memory_search` + `debug_memory_list` first |

Do not store large file contents in memory. Store only the key facts, decisions, and patterns.

---

## AI Behavior Guidelines

### Before making any change
1. Read the file you are about to edit
2. Search for all callers of the function you are changing (`file_search`)
3. Understand the return type — core modules return `str`, plugin tools return `str`, `call_tool` returns `list[TextContent]`

### When the user asks to add a tool
1. Implement the function in the correct `core/` module or new plugin
2. Add the tool definition to `ALL_TOOLS` in `server.py`
3. Add the handler in `call_tool()` in `server.py`
4. If it's a plugin tool, add to PLUGIN_MAP and setup_wizard ALL_PLUGINS

### When the user asks to add a plugin
Follow the plugin pattern exactly. Do not create additional abstraction layers. One `_ops.py` file with a `TOOLS` dict is the complete pattern.

### When debugging a tool call failure
1. Check `auth.py` — is token valid?
2. Check `ACTIVE_PROJECT_PATH` — is it the right project?
3. Check `_project_frameworks()` — is the plugin loaded?
4. Check the plugin's `TOOLS` dict — is the function registered?
5. Check `_call_plugin_tool()` — is the parameter name matching the function signature?

### Do not
- Add comments explaining what code does (code should be self-explanatory)
- Reformat files that are not being modified
- Add type annotations to files that don't already use them
- Create helper files or abstractions for a single use case
- Suggest refactoring while implementing a feature request

---

## Areas Requiring Extra Care

| File/Area | Why |
|-----------|-----|
| `auth.py` | Security — changing expiry or token format breaks all sessions |
| `server.py` `ALL_TOOLS` | Adding without handler = runtime crash; removing = feature loss |
| `config.py` merge logic | Frappe multi-bench config depends on deep merge behavior |
| `plugins/__init__.py` PLUGIN_MAP | Wrong module path silently disables entire framework |
| `core/shell_executor.py` BLOCKED_COMMANDS | Removing entries creates security risk |
| `core/file_manager.py` `_safe_path()` | Path jail — weakening it allows directory traversal |
| `ACTIVE_PROJECT_PATH` in `server.py` | Global mutable — only `switch_project` should write it |

---

## Development Checklist

Before submitting any change:

- [ ] Read all modified files before changing them
- [ ] Verified the function return type matches what callers expect (always `str` for plugins)
- [ ] Added both the tool definition in `ALL_TOOLS` AND the handler in `call_tool()` (if adding a tool)
- [ ] Tested that `python -c "import server"` runs without errors
- [ ] Verified that existing tools still work (no regressions in `call_tool` dispatch)
- [ ] Did not modify `auth.py` unless the task specifically requires it
- [ ] Did not add features beyond what was requested
