"""
Universal Dev MCP - MCP Server
All tools registered here. Auth checked on every tool call.
"""
import inspect
import json
import os
import sys
import importlib
from pathlib import Path

import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route
from mcp.server import Server
from mcp import types

import auth
from config import load_project_config, load_global_config, load_state, save_state
from core import shell_executor
from core import agent_planner

from core import file_manager
from core import git_ops
from core import env_manager
from core import log_reader
from core import port_manager
from core import docker_ops
from core import test_runner
from core import package_manager
from core import project_context
from core import project_detector
from core import memory_manager
from core import browser_automation
from core import desktop_control
from plugins import load_plugin_tools

# Global project path (set at startup, can be changed per-session via switch_project)
PROJECT_PATH = os.environ.get("MCP_PROJECT_PATH", os.getcwd())
# Restore last active path from state.json, fallback to PROJECT_PATH
ACTIVE_PROJECT_PATH = load_state().get("active_project_path", PROJECT_PATH)

mcp_server = Server("universal-dev-mcp")

# ─────────────────────────────────────────────
# TOOL DEFINITIONS
# ─────────────────────────────────────────────

ALL_TOOLS = [
    # AUTH
    types.Tool(name="verify_session", description="OTP verify karo — pehle ye tool use karo", inputSchema={
        "type": "object", "properties": {"code": {"type": "string", "description": "6-digit OTP code. Empty rakhne par OTP bheja jayega."}}, "required": []
    }),

    # PROJECT CONTEXT
    types.Tool(name="switch_project", description=(
        "Naye project ya framework par switch karo. "
        "Jab user kisi aur project/framework par kaam karna chahe to HAMESHA pehle yeh tool call karo. "
        "Sirf 'name' do (e.g. 'vue', 'frappe', 'app') — path automatically dhundha jayega. "
        "Ya direct 'project_path' bhi de sakte ho."
    ), inputSchema={
        "type": "object",
        "properties": {
            "session_token": {"type": "string"},
            "name": {"type": "string", "description": "Project name jaise setup mein register kiya tha (e.g. 'vue', 'frappe', 'myapp')"},
            "project_path": {"type": "string", "description": "Direct absolute path — sirf tab do jab name se kaam na ho"},
        },
        "required": ["session_token"],
    }),
    types.Tool(name="register_project", description=(
        "Naya project registry mein add karo taaki baad mein sirf naam se switch ho sake. "
        "Wizard ke baad bhi naye projects add karne ke liye yeh use karo."
    ), inputSchema={
        "type": "object",
        "properties": {
            "session_token": {"type": "string"},
            "name": {"type": "string", "description": "Short naam (e.g. 'vue', 'frappe', 'myapp')"},
            "project_path": {"type": "string", "description": "Project ka absolute path"},
        },
        "required": ["session_token", "name", "project_path"],
    }),
    types.Tool(name="list_projects", description="Saare registered projects aur unka active status dekho", inputSchema={
        "type": "object", "properties": {"session_token": {"type": "string"}}, "required": ["session_token"]
    }),
    types.Tool(name="deregister_project", description="Registry se project hataao (path delete nahi hoga, sirf naam mapping remove hogi)", inputSchema={
        "type": "object",
        "properties": {
            "session_token": {"type": "string"},
            "name": {"type": "string", "description": "Project naam jo remove karna hai"},
        },
        "required": ["session_token", "name"],
    }),
    types.Tool(name="reload_plugins", description="active_plugins config se nayi frameworks load karo bina server restart kiye", inputSchema={
        "type": "object", "properties": {"session_token": {"type": "string"}}, "required": ["session_token"]
    }),
    types.Tool(name="project_context", description="Current project info load karo (framework, config, active path)", inputSchema={
        "type": "object", "properties": {"session_token": {"type": "string"}}, "required": ["session_token"]
    }),
    types.Tool(name="confirm_framework", description="Framework confirm karo aur .mcp-config.json save karo", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "framework": {"type": "string", "description": "Framework naam: django, nextjs, laravel, frappe, react, generic etc."},
            "extra_config": {"type": "object", "description": "Optional extra config (db, run_command etc.)"}
        }, "required": ["session_token", "framework"]
    }),

    # SHELL
    types.Tool(name="shell_run", description="Koi bhi terminal command chalao project directory mein", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "command": {"type": "string"},
            "timeout": {"type": "integer", "default": 60}
        }, "required": ["session_token", "command"]
    }),

    # FILE MANAGER
    types.Tool(name="file_read", description="Koi bhi file padhna", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "path": {"type": "string", "description": "Project ke andar relative path"}
        }, "required": ["session_token", "path"]
    }),
    types.Tool(name="file_write", description="Koi bhi file likhna ya banana", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "path": {"type": "string"},
            "content": {"type": "string"}
        }, "required": ["session_token", "path", "content"]
    }),
    types.Tool(name="file_list", description="Directory contents dekhna", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "path": {"type": "string", "default": "."}
        }, "required": ["session_token"]
    }),
    types.Tool(name="file_search", description="Project mein text search karna", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "pattern": {"type": "string"},
            "file_pattern": {"type": "string", "default": "*"}
        }, "required": ["session_token", "pattern"]
    }),

    # GIT
    types.Tool(name="git_status", description="Git status, log, diff dekhna", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "action": {"type": "string", "enum": ["status", "log", "diff", "branch"], "default": "status"}
        }, "required": ["session_token"]
    }),
    types.Tool(name="git_commit", description="Git add + commit karna", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "message": {"type": "string"},
            "push": {"type": "boolean", "default": False}
        }, "required": ["session_token", "message"]
    }),

    # ENV
    types.Tool(name="env_read", description=".env file safely padhna (secrets masked)", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "env_file": {"type": "string", "default": ".env"},
            "hide_secrets": {"type": "boolean", "default": True}
        }, "required": ["session_token"]
    }),

    # LOGS
    types.Tool(name="log_tail", description="Kisi bhi log file ke last N lines padhna", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "log_path": {"type": "string"},
            "n": {"type": "integer", "default": 20},
            "pattern": {"type": "string", "description": "Optional: sirf matching lines dikhao"}
        }, "required": ["session_token", "log_path"]
    }),

    # PORT
    types.Tool(name="port_check", description="Kaun sa port chal raha hai check karo", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "port": {"type": "integer", "description": "Specific port (optional)"}
        }, "required": ["session_token"]
    }),

    # DOCKER
    types.Tool(name="docker_ps", description="Docker containers list karo", inputSchema={
        "type": "object", "properties": {"session_token": {"type": "string"}}, "required": ["session_token"]
    }),
    types.Tool(name="docker_logs", description="Docker container logs padhna", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "container": {"type": "string"},
            "n": {"type": "integer", "default": 20}
        }, "required": ["session_token", "container"]
    }),

    # TESTS
    types.Tool(name="test_run", description="Tests chalana (auto-detect: pytest/jest/phpunit)", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "path": {"type": "string", "default": ""}
        }, "required": ["session_token"]
    }),

    # PACKAGES
    types.Tool(name="package_install", description="Package install karna (auto-detect: pip/npm/composer)", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "package": {"type": "string", "description": "Package naam (empty = install all from lockfile)"}
        }, "required": ["session_token"]
    }),

    # MEMORY (legacy)
    types.Tool(name="memory_save", description="Kuch yaad rakhna Claude ke liye", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "key": {"type": "string"},
            "value": {"type": "string"}
        }, "required": ["session_token", "key", "value"]
    }),
    types.Tool(name="memory_get", description="Pehle save ki gayi memory padhna", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "key": {"type": "string"}
        }, "required": ["session_token", "key"]
    }),
    types.Tool(name="memory_list", description="Sari saved memories dekhna", inputSchema={
        "type": "object", "properties": {"session_token": {"type": "string"}}, "required": ["session_token"]
    }),

    # PROJECT/DECISION/DEBUG/SEMANTIC MEMORY (user_id based)
    types.Tool(name="project_memory_set", description="Project memory save (user_id based)", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "user_id": {"type": "string"},
            "key": {"type": "string"},
            "value": {"type": "string"}
        }, "required": ["session_token", "user_id", "key", "value"]
    }),
    types.Tool(name="project_memory_get", description="Project memory get (user_id based)", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "user_id": {"type": "string"},
            "key": {"type": "string"}
        }, "required": ["session_token", "user_id", "key"]
    }),
    types.Tool(name="project_memory_list", description="Project memory list (user_id based)", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "user_id": {"type": "string"}
        }, "required": ["session_token", "user_id"]
    }),

    types.Tool(name="decision_memory_add", description="Decision memory add (user_id based)", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "user_id": {"type": "string"},
            "decision_id": {"type": "string"},
            "decision_text": {"type": "string"},
            "metadata_json": {"type": "object", "description": "Optional metadata as JSON object"}
        }, "required": ["session_token", "user_id", "decision_id", "decision_text"]
    }),
    types.Tool(name="decision_memory_search", description="Decision memory search (keyword overlap) (user_id based)", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "user_id": {"type": "string"},
            "query": {"type": "string"},
            "limit": {"type": "integer", "default": 5}
        }, "required": ["session_token", "user_id", "query"]
    }),

    types.Tool(name="debug_memory_add", description="Debug memory add (user_id based)", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "user_id": {"type": "string"},
            "scope": {"type": "string"},
            "error_text": {"type": "string"},
            "context_text": {"type": "string"},
            "metadata_json": {"type": "object", "description": "Optional metadata as JSON object"}
        }, "required": ["session_token", "user_id", "scope", "error_text"]
    }),
    types.Tool(name="debug_memory_list", description="Debug memory list (user_id based)", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "user_id": {"type": "string"},
            "scope": {"type": "string"},
            "limit": {"type": "integer", "default": 50}
        }, "required": ["session_token", "user_id"]
    }),

    types.Tool(name="semantic_memory_add", description="Semantic memory add (user_id based)", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "user_id": {"type": "string"},
            "tag": {"type": "string"},
            "text": {"type": "string"},
            "metadata_json": {"type": "object", "description": "Optional metadata as JSON object"}
        }, "required": ["session_token", "user_id", "tag", "text"]
    }),
    types.Tool(name="semantic_memory_search", description="Semantic memory search (keyword overlap) (user_id based)", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "user_id": {"type": "string"},
            "query": {"type": "string"},
            "limit": {"type": "integer", "default": 5}
        }, "required": ["session_token", "user_id", "query"]
    }),

    # AGENT PLANNER (internal planner output)
    types.Tool(name="generate_plan", description="Request ke basis par tool-use plan generate karta hai (uses memories)", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "user_id": {"type": "string"},
            "request_text": {"type": "string"},
            "framework_hint": {"type": "string"}
        }, "required": ["session_token", "user_id", "request_text"]
    }),


    # BROWSER
    types.Tool(name="browser_launch", description="Browser launch karo (chromium ya firefox)", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "browser_type": {"type": "string", "default": "chromium"}
        }, "required": ["session_token"]
    }),
    types.Tool(name="browser_navigate", description="Browser mein URL kholo", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "url": {"type": "string"},
            "screenshot": {"type": "boolean", "default": True}
        }, "required": ["session_token", "url"]
    }),
    types.Tool(name="browser_screenshot", description="Browser ka screenshot lo", inputSchema={
        "type": "object", "properties": {"session_token": {"type": "string"}}, "required": ["session_token"]
    }),
    types.Tool(name="browser_click", description="Browser mein element click karo (CSS selector ya text)", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "selector": {"type": "string"},
            "screenshot": {"type": "boolean", "default": True}
        }, "required": ["session_token", "selector"]
    }),
    types.Tool(name="browser_click_at", description="Browser mein exact pixel coordinates par click karo", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "x": {"type": "integer"},
            "y": {"type": "integer"},
            "screenshot": {"type": "boolean", "default": True}
        }, "required": ["session_token", "x", "y"]
    }),
    types.Tool(name="browser_type", description="Browser input field mein text type karo", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "selector": {"type": "string"},
            "text": {"type": "string"},
            "clear_first": {"type": "boolean", "default": True}
        }, "required": ["session_token", "selector", "text"]
    }),
    types.Tool(name="browser_press_key", description="Browser mein keyboard key press karo (e.g. Enter, Tab, Control+a)", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "key": {"type": "string"}
        }, "required": ["session_token", "key"]
    }),
    types.Tool(name="browser_get_content", description="Current page ka text content lo (first 8000 chars)", inputSchema={
        "type": "object", "properties": {"session_token": {"type": "string"}}, "required": ["session_token"]
    }),
    types.Tool(name="browser_get_element", description="Page par specific element dhundho aur uska content lo", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "selector": {"type": "string"}
        }, "required": ["session_token", "selector"]
    }),
    types.Tool(name="browser_wait", description="Page load ya animation ka wait karo, phir screenshot lo", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "milliseconds": {"type": "integer", "default": 2000}
        }, "required": ["session_token"]
    }),
    types.Tool(name="browser_save_session", description="Current browser session (cookies) disk par save karo", inputSchema={
        "type": "object", "properties": {"session_token": {"type": "string"}}, "required": ["session_token"]
    }),
    types.Tool(name="browser_close", description="Browser band karo, session auto-save hoga", inputSchema={
        "type": "object", "properties": {"session_token": {"type": "string"}}, "required": ["session_token"]
    }),

    # DESKTOP
    types.Tool(name="desktop_screenshot", description="Desktop ka screenshot lo (GNOME Wayland/XWayland)", inputSchema={
        "type": "object", "properties": {"session_token": {"type": "string"}}, "required": ["session_token"]
    }),
    types.Tool(name="desktop_open_app", description="Desktop application ya URL kholo", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "command": {"type": "string"},
            "args": {"type": "string", "default": ""},
            "screenshot": {"type": "boolean", "default": True}
        }, "required": ["session_token", "command"]
    }),
    types.Tool(name="desktop_click", description="Desktop par exact coordinates par click karo (XTEST/XWayland)", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "x": {"type": "integer"},
            "y": {"type": "integer"},
            "button": {"type": "string", "default": "left"}
        }, "required": ["session_token", "x", "y"]
    }),
    types.Tool(name="desktop_type", description="Focused window mein text type karo (Unicode support)", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "text": {"type": "string"}
        }, "required": ["session_token", "text"]
    }),
    types.Tool(name="desktop_key", description="Keyboard shortcut press karo (e.g. ctrl+c, alt+tab, enter)", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "keys": {"type": "string"}
        }, "required": ["session_token", "keys"]
    }),
    types.Tool(name="desktop_get_windows", description="Saari open windows ki list lo", inputSchema={
        "type": "object", "properties": {"session_token": {"type": "string"}}, "required": ["session_token"]
    }),
]


@mcp_server.list_tools()
async def list_tools() -> list[types.Tool]:
    return ALL_TOOLS + _build_plugin_tool_definitions()


def _project_frameworks() -> list[str]:
    """Return active plugins — from global config's active_plugins (set by setup_wizard),
    with fallback to project .mcp-config.json framework key."""
    global_cfg = load_global_config()
    active = global_cfg.get("active_plugins")
    if isinstance(active, list) and active:
        plugins = [str(f).strip().lower() for f in active if f]
        if "generic" not in plugins:
            plugins.append("generic")
        return plugins

    # Fallback: old single/multi framework config
    cfg = load_project_config(PROJECT_PATH)
    multi = cfg.get("frameworks")
    if isinstance(multi, list) and multi:
        return [str(f).strip().lower() for f in multi if f]
    single = cfg.get("framework", "generic")
    return [str(single).strip().lower()]


def _active_plugin_tools() -> dict:
    """Load tools for all active frameworks, merging them together."""
    all_tools: dict = {}
    for fw in _project_frameworks():
        all_tools.update(load_plugin_tools(fw))
    return all_tools


def _json_schema_type(annotation) -> str:
    if annotation is int:
        return "integer"
    if annotation is float:
        return "number"
    if annotation is bool:
        return "boolean"
    return "string"


def _build_plugin_tool_definitions() -> list[types.Tool]:
    definitions = []

    for name, meta in _active_plugin_tools().items():
        fn = meta.get("fn")
        if not callable(fn):
            continue

        properties = {"session_token": {"type": "string"}}
        required = ["session_token"]
        signature = inspect.signature(fn)

        for param_name, param in signature.parameters.items():
            if param_name == "project_path":
                continue

            schema = {"type": _json_schema_type(param.annotation)}
            if param.default is not inspect._empty:
                schema["default"] = param.default
            else:
                required.append(param_name)

            properties[param_name] = schema

        definitions.append(
            types.Tool(
                name=name,
                description=meta.get("description", "plugin tool"),
                inputSchema={
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            )
        )

    return definitions


def _call_plugin_tool(name: str, arguments: dict, project_path: str) -> str | None:
    meta = _active_plugin_tools().get(name)
    if not meta:
        return None

    fn = meta.get("fn")
    if not callable(fn):
        return f"ERROR: Plugin tool is not callable: {name}"

    signature = inspect.signature(fn)
    kwargs = {}
    for param_name in signature.parameters:
        if param_name == "project_path":
            kwargs[param_name] = project_path
        elif param_name in arguments:
            kwargs[param_name] = arguments[param_name]

    result = fn(**kwargs)
    if isinstance(result, (dict, list)):
        return json.dumps(result, indent=2, ensure_ascii=False)
    if result is None:
        return ""
    return str(result)


def _check_auth(args: dict) -> str | None:
    token = args.get("session_token", "")
    return auth.auth_required(token)


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    global ACTIVE_PROJECT_PATH

    def r(text) -> list:
        if isinstance(text, dict) and text.get("_image"):
            return [types.ImageContent(type="image", data=text["data"], mimeType=f"image/{text.get('format', 'jpeg')}")]
        return [types.TextContent(type="text", text=str(text))]

    # ── AUTH TOOL (no session needed) ──
    if name == "verify_session":
        code = arguments.get("code", "").strip()
        if not code:
            msg = auth.request_otp()
            return r(f"OTP bheja gaya. {msg}\n\nverify_session(code='XXXXXX') call karo.")
        result = auth.verify_otp(code)
        if result["success"]:
            return r(f"✅ {result['message']}\n\nSession Token: {result['session_token']}\n\nAb ye token saare tools mein pass karo.")
        return r(f"❌ {result['message']}")

    # ── AUTH CHECK for all other tools ──
    err = _check_auth(arguments)
    if err:
        return r(err)

    pp = ACTIVE_PROJECT_PATH  # uses current active path (can be changed by switch_project)

    # ── TOOL DISPATCH ──
    try:
        if name == "switch_project":
            proj_name = arguments.get("name", "").strip().lower()
            proj_path = arguments.get("project_path", "").strip()

            # Name-based lookup from registry
            if proj_name and not proj_path:
                global_cfg = load_global_config()
                registry = global_cfg.get("projects", [])
                # Match by name or framework
                match = next(
                    (p for p in registry if p.get("name", "").lower() == proj_name
                     or p.get("framework", "").lower() == proj_name),
                    None
                )
                if not match:
                    names = [p.get("name") for p in registry]
                    return r(
                        f"❌ '{proj_name}' registry mein nahi mila.\n"
                        f"Registered projects: {', '.join(names) if names else 'koi nahi'}\n\n"
                        f"Naya project register karne ke liye `register_project` tool use karo."
                    )
                proj_path = match["path"]

            if not proj_path:
                return r("❌ 'name' ya 'project_path' mein se koi ek do.")
            if not Path(proj_path).exists():
                return r(f"❌ Path exist nahi karta: {proj_path}")

            ACTIVE_PROJECT_PATH = proj_path
            save_state({"active_project_path": proj_path})
            ctx = project_context.get_project_context(proj_path)
            return r(f"✅ Project switched!\nActive path: {proj_path}\n\n{ctx}")

        elif name == "register_project":
            reg_name = arguments.get("name", "").strip().lower().replace(" ", "_")
            reg_path = arguments.get("project_path", "").strip()
            if not reg_name or not reg_path:
                return r("❌ name aur project_path dono chahiye.")
            if not Path(reg_path).exists():
                return r(f"❌ Path exist nahi karta: {reg_path}")
            detected = project_detector.detect_framework(reg_path)
            fw = detected[0]["framework"] if detected else "generic"
            global_cfg = load_global_config()
            registry = global_cfg.get("projects", [])
            registry = [p for p in registry if p.get("name") != reg_name]  # update if exists
            registry.append({"name": reg_name, "path": reg_path, "framework": fw})
            global_cfg["projects"] = registry
            from config import save_global_config
            save_global_config(global_cfg)
            return r(f"✅ Registered: '{reg_name}' → {reg_path} [{fw}]\n\nAb 'switch_project(name=\"{reg_name}\")' se switch kar sakte ho.")

        elif name == "list_projects":
            global_cfg = load_global_config()
            registry = global_cfg.get("projects", [])
            if not registry:
                return r("Koi project registered nahi hai.\n`register_project` tool se add karo.")
            lines = ["📋 Registered Projects:\n"]
            for p in registry:
                active_marker = " ◀ ACTIVE" if p["path"] == ACTIVE_PROJECT_PATH else ""
                lines.append(f"  • {p['name']:15} [{p['framework']:10}] → {p['path']}{active_marker}")
            lines.append(f"\n💡 Switch karne ke liye: switch_project(name='<naam>')")
            return r("\n".join(lines))

        elif name == "deregister_project":
            reg_name = arguments.get("name", "").strip().lower()
            if not reg_name:
                return r("❌ name do.")
            global_cfg = load_global_config()
            registry = global_cfg.get("projects", [])
            new_registry = [p for p in registry if p.get("name") != reg_name]
            if len(new_registry) == len(registry):
                return r(f"❌ '{reg_name}' registry mein nahi mila.")
            global_cfg["projects"] = new_registry
            from config import save_global_config
            save_global_config(global_cfg)
            return r(f"✅ '{reg_name}' registry se remove kar diya.\nBaaki projects: {[p['name'] for p in new_registry]}")

        elif name == "reload_plugins":
            old_fw = _project_frameworks()
            global_cfg = load_global_config()
            new_fw = global_cfg.get("active_plugins", ["generic"])
            return r(
                f"✅ Plugins reloaded.\n"
                f"Active plugins: {', '.join(new_fw)}\n\n"
                f"Note: Naye plugin tools next tool call se available honge."
            )

        elif name == "project_context":
            return r(project_context.get_project_context(pp))

        elif name == "confirm_framework":
            fw = arguments.get("framework", "generic")
            extra = arguments.get("extra_config", {})
            return r(project_context.confirm_framework(pp, fw, extra))

        elif name == "shell_run":
            return r(shell_executor.shell_run(arguments["command"], pp, arguments.get("timeout", 60)))

        elif name == "file_read":
            return r(file_manager.file_read(pp, arguments["path"]))

        elif name == "file_write":
            return r(file_manager.file_write(pp, arguments["path"], arguments["content"]))

        elif name == "file_list":
            return r(file_manager.file_list(pp, arguments.get("path", ".")))

        elif name == "file_search":
            return r(file_manager.file_search(pp, arguments["pattern"], arguments.get("file_pattern", "*")))

        elif name == "git_status":
            action = arguments.get("action", "status")
            fn_map = {"status": git_ops.git_status, "log": git_ops.git_log, "diff": git_ops.git_diff, "branch": git_ops.git_branch}
            return r(fn_map.get(action, git_ops.git_status)(pp))

        elif name == "git_commit":
            result = git_ops.git_commit(pp, arguments["message"])
            if arguments.get("push"):
                result += "\n\n" + git_ops.git_push(pp)
            return r(result)

        elif name == "env_read":
            return r(env_manager.env_read(pp, arguments.get("env_file", ".env"), arguments.get("hide_secrets", True)))

        elif name == "log_tail":
            pattern = arguments.get("pattern")
            if pattern:
                return r(log_reader.log_grep(pp, arguments["log_path"], pattern, arguments.get("n", 50)))
            return r(log_reader.log_tail(pp, arguments["log_path"], arguments.get("n", 50)))

        elif name == "port_check":
            return r(port_manager.port_check(arguments.get("port")))

        elif name == "docker_ps":
            return r(docker_ops.docker_ps(pp))

        elif name == "docker_logs":
            return r(docker_ops.docker_logs(arguments["container"], arguments.get("n", 50)))

        elif name == "test_run":
            return r(test_runner.test_run(pp, arguments.get("path", "")))

        elif name == "package_install":
            return r(package_manager.package_install(pp, arguments.get("package", "")))

        elif name == "memory_save":
            return r(memory_manager.memory_save(pp, arguments["key"], arguments["value"]))

        elif name == "memory_get":
            return r(memory_manager.memory_get(pp, arguments["key"]))

        elif name == "memory_list":
            return r(memory_manager.memory_list(pp))

        elif name == "project_memory_set":
            return r(memory_manager.project_memory_set(pp, arguments["user_id"], arguments["key"], arguments["value"]))

        elif name == "project_memory_get":
            return r(memory_manager.project_memory_get(pp, arguments["user_id"], arguments["key"]))

        elif name == "project_memory_list":
            return r(memory_manager.project_memory_list(pp, arguments["user_id"]))

        elif name == "decision_memory_add":
            metadata = arguments.get("metadata_json", {})
            return r(memory_manager.decision_memory_add(
                pp,
                arguments["user_id"],
                arguments["decision_id"],
                arguments["decision_text"],
                json.dumps(metadata, ensure_ascii=False),
            ))

        elif name == "decision_memory_search":
            return r(memory_manager.decision_memory_search(
                pp,
                arguments["user_id"],
                arguments["query"],
                arguments.get("limit", 5),
            ))

        elif name == "debug_memory_add":
            metadata = arguments.get("metadata_json", {})
            return r(memory_manager.debug_memory_add(
                pp,
                arguments["user_id"],
                arguments["scope"],
                arguments["error_text"],
                arguments.get("context_text", ""),
                json.dumps(metadata, ensure_ascii=False),
            ))

        elif name == "debug_memory_list":
            return r(memory_manager.debug_memory_list(
                pp,
                arguments["user_id"],
                arguments.get("scope"),
                arguments.get("limit", 50),
            ))

        elif name == "semantic_memory_add":
            metadata = arguments.get("metadata_json", {})
            return r(memory_manager.semantic_memory_add(
                pp,
                arguments["user_id"],
                arguments["tag"],
                arguments["text"],
                json.dumps(metadata, ensure_ascii=False),
            ))

        elif name == "semantic_memory_search":
            return r(memory_manager.semantic_memory_search(
                pp,
                arguments["user_id"],
                arguments["query"],
                arguments.get("limit", 5),
            ))

        elif name == "generate_plan":
            return r(agent_planner.generate_plan(
                pp,
                arguments["user_id"],
                arguments["request_text"],
                arguments.get("framework_hint"),
            ))

        elif name == "browser_launch":
            return r(browser_automation.browser_launch(arguments.get("browser_type", "chromium")))

        elif name == "browser_navigate":
            return r(browser_automation.browser_navigate(arguments["url"], arguments.get("screenshot", True)))

        elif name == "browser_screenshot":
            return r(browser_automation.browser_screenshot())

        elif name == "browser_click":
            return r(browser_automation.browser_click(arguments["selector"], arguments.get("screenshot", True)))

        elif name == "browser_click_at":
            return r(browser_automation.browser_click_at(arguments["x"], arguments["y"], arguments.get("screenshot", True)))

        elif name == "browser_type":
            return r(browser_automation.browser_type(arguments["selector"], arguments["text"], arguments.get("clear_first", True)))

        elif name == "browser_press_key":
            return r(browser_automation.browser_press_key(arguments["key"]))

        elif name == "browser_get_content":
            return r(browser_automation.browser_get_content())

        elif name == "browser_get_element":
            return r(browser_automation.browser_get_element(arguments["selector"]))

        elif name == "browser_wait":
            return r(browser_automation.browser_wait(arguments.get("milliseconds", 2000)))

        elif name == "browser_save_session":
            return r(browser_automation.browser_save_session())

        elif name == "browser_close":
            return r(browser_automation.browser_close())

        elif name == "desktop_screenshot":
            return r(desktop_control.desktop_screenshot())

        elif name == "desktop_open_app":
            return r(desktop_control.desktop_open_app(arguments["command"], arguments.get("args", ""), arguments.get("screenshot", True)))

        elif name == "desktop_click":
            return r(desktop_control.desktop_click(arguments["x"], arguments["y"], arguments.get("button", "left")))

        elif name == "desktop_type":
            return r(desktop_control.desktop_type(arguments["text"]))

        elif name == "desktop_key":
            return r(desktop_control.desktop_key(arguments["keys"]))

        elif name == "desktop_get_windows":
            return r(desktop_control.desktop_get_windows())

        else:
            # Framework switch check — warn AI before executing plugin tool
            switch_warning = project_context.check_framework_switch(pp)
            plugin_result = _call_plugin_tool(name, arguments, pp)
            if plugin_result is not None:
                if switch_warning:
                    return r(f"{switch_warning}\n\n{'─'*50}\n\n{plugin_result}")
                return r(plugin_result)
            return r(f"❌ Unknown tool: {name}")

    except Exception as e:
        return r(f"❌ Tool error ({name}): {e}")


# ─────────────────────────────────────────────
# ASGI APP SETUP — Streamable HTTP transport
# ─────────────────────────────────────────────

def _build_app() -> Starlette:
    import contextlib
    import json as _json
    from starlette.requests import Request
    from starlette.responses import JSONResponse
    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
    from mcp.server.fastmcp.server import StreamableHTTPASGIApp

    session_manager = StreamableHTTPSessionManager(
        app=mcp_server,
        json_response=False,
        stateless=True,
    )
    asgi_app = StreamableHTTPASGIApp(session_manager)

    async def health_endpoint(request: Request):
        cfg = load_global_config()
        return JSONResponse({
            "status": "ok",
            "active_project": ACTIVE_PROJECT_PATH,
            "active_plugins": _project_frameworks(),
            "tunnel_provider": cfg.get("tunnel_provider", "none"),
            "tunnel_url": cfg.get("tunnel_url", ""),
        })

    @contextlib.asynccontextmanager
    async def lifespan(_app):
        async with session_manager.run():
            yield

    return Starlette(
        routes=[
            Route("/mcp", endpoint=asgi_app, methods=["GET", "POST", "DELETE"]),
            Route("/health", endpoint=health_endpoint, methods=["GET"]),
        ],
        lifespan=lifespan,
    )


def run_server(project_path: str, port: int):
    global PROJECT_PATH
    PROJECT_PATH = project_path
    os.environ["MCP_PROJECT_PATH"] = project_path
    app = _build_app()
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
