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
from mcp.server.sse import SseServerTransport
from mcp import types

import auth
from config import load_project_config
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

# Global project path (set at startup)
PROJECT_PATH = os.environ.get("MCP_PROJECT_PATH", os.getcwd())

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
    types.Tool(name="project_context", description="Project info load karo (framework, config)", inputSchema={
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
            "n": {"type": "integer", "default": 50},
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
            "n": {"type": "integer", "default": 50}
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
    types.Tool(name="browser_navigate", description="Browser mein URL kholo", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "url": {"type": "string"}
        }, "required": ["session_token", "url"]
    }),
    types.Tool(name="browser_get_content", description="Current page ka text content lo", inputSchema={
        "type": "object", "properties": {"session_token": {"type": "string"}}, "required": ["session_token"]
    }),
    types.Tool(name="browser_click", description="Browser mein element click karo", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "selector": {"type": "string"}
        }, "required": ["session_token", "selector"]
    }),
    types.Tool(name="browser_screenshot", description="Browser screenshot lo", inputSchema={
        "type": "object", "properties": {"session_token": {"type": "string"}}, "required": ["session_token"]
    }),

    # DESKTOP
    types.Tool(name="desktop_screenshot", description="Desktop ka screenshot lo", inputSchema={
        "type": "object", "properties": {"session_token": {"type": "string"}}, "required": ["session_token"]
    }),
    types.Tool(name="desktop_click", description="Desktop par click karo (x, y coordinates)", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "x": {"type": "integer"},
            "y": {"type": "integer"}
        }, "required": ["session_token", "x", "y"]
    }),
    types.Tool(name="desktop_type", description="Keyboard se text type karo", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "text": {"type": "string"}
        }, "required": ["session_token", "text"]
    }),
    types.Tool(name="desktop_key", description="Keyboard shortcut press karo (e.g. ctrl+c)", inputSchema={
        "type": "object", "properties": {
            "session_token": {"type": "string"},
            "keys": {"type": "string"}
        }, "required": ["session_token", "keys"]
    }),
]


@mcp_server.list_tools()
async def list_tools() -> list[types.Tool]:
    return ALL_TOOLS + _build_plugin_tool_definitions()


def _project_framework() -> str:
    cfg = load_project_config(PROJECT_PATH)
    return cfg.get("framework", "generic")


def _active_plugin_tools() -> dict:
    return load_plugin_tools(_project_framework())


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
                description=meta.get("description", f"{_project_framework()} plugin tool"),
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
    def r(text: str) -> list[types.TextContent]:
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

    pp = PROJECT_PATH  # project path

    # ── TOOL DISPATCH ──
    try:
        if name == "project_context":
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

        elif name == "browser_navigate":
            return r(browser_automation.browser_navigate(arguments["url"]))


        elif name == "browser_get_content":
            return r(browser_automation.browser_get_content())

        elif name == "browser_click":
            return r(browser_automation.browser_click(arguments["selector"]))

        elif name == "browser_screenshot":
            return r(browser_automation.browser_screenshot())

        elif name == "desktop_screenshot":
            return r(desktop_control.desktop_screenshot())

        elif name == "desktop_click":
            return r(desktop_control.desktop_click(arguments["x"], arguments["y"]))

        elif name == "desktop_type":
            return r(desktop_control.desktop_type(arguments["text"]))

        elif name == "desktop_key":
            return r(desktop_control.desktop_key(arguments["keys"]))

        else:
            plugin_result = _call_plugin_tool(name, arguments, pp)
            if plugin_result is not None:
                return r(plugin_result)
            return r(f"❌ Unknown tool: {name}")

    except Exception as e:
        return r(f"❌ Tool error ({name}): {e}")


# ─────────────────────────────────────────────
# ASGI APP SETUP
# ─────────────────────────────────────────────
sse_transport = SseServerTransport("/messages/")


async def sse_handler(request):
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as (read_stream, write_stream):
        await mcp_server.run(
            read_stream, write_stream,
            mcp_server.create_initialization_options()
        )


async def messages_handler(request):
    await sse_transport.handle_post_message(
        request.scope, request.receive, request._send
    )


app = Starlette(routes=[
    Route("/sse", endpoint=sse_handler),
    Route("/messages/", endpoint=messages_handler, methods=["POST"]),
])


def run_server(project_path: str, port: int):
    global PROJECT_PATH
    PROJECT_PATH = project_path
    os.environ["MCP_PROJECT_PATH"] = project_path
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
