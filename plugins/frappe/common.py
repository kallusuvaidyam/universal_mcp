"""Shared helpers for the Frappe plugin."""
from __future__ import annotations

import ast
import json
import os
import re
import shlex
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from config import load_project_config


DEFAULT_BLOCKED_COMMANDS = ["drop-site", "drop-database", "destroy", "drop"]
DEFAULT_BLOCKED_EXPRESSIONS = [
    "drop",
    "delete from",
    "truncate",
    "os.system",
    "subprocess",
    "__import__",
    "open(",
    "rm ",
    "shutil.rmtree",
    "exec(",
    "eval(",
]
DEFAULT_WARN_EXPRESSIONS = [
    "frappe.db.set_value",
    "frappe.delete_doc",
    "frappe.submit",
    "frappe.db.commit",
]
SITE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
EXCLUDED_SITE_DIRS = {"assets", "apps"}
BENCH_RUNNING_CACHE: dict[str, tuple[bool, float]] = {}
BENCH_CACHE_TTL = 60


@dataclass
class SiteCredentials:
    api_key: str = ""
    api_secret: str = ""
    port: int | None = None
    admin_user: str = "Administrator"
    admin_password: str = ""


@dataclass
class BenchContext:
    project_path: str
    bench_id: str
    bench_path: Path
    bench_cmd: str
    node_version: str | None
    site: str
    site_credentials: SiteCredentials
    config: dict


def json_text(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


def parse_json_input(raw: str, default: Any) -> Any:
    if raw is None:
        return default
    if isinstance(raw, (dict, list)):
        return raw

    text = str(raw).strip()
    if not text:
        return default

    return json.loads(text)


def load_frappe_config(project_path: str) -> dict:
    raw = load_project_config(project_path)
    frappe_cfg = raw.get("frappe", {})

    if not isinstance(frappe_cfg, dict):
        frappe_cfg = {}

    merged = dict(raw)
    merged.update(frappe_cfg)
    return merged


def detect_bench_path(project_path: str, config: dict) -> Path:
    explicit = config.get("bench_path")
    if explicit:
        return Path(explicit).expanduser().resolve()

    current = Path(project_path).expanduser().resolve()
    for path in [current, *current.parents]:
        if (path / "sites").is_dir() and (path / "apps").is_dir():
            return path
    return current


def guess_bench_cmd(bench_path: Path, config: dict) -> str:
    explicit = str(config.get("bench_cmd", "")).strip()
    if explicit:
        return explicit

    bench_bin = bench_path / "env" / "bin" / "bench"
    if bench_bin.exists():
        return str(bench_bin)

    return "bench"


def parse_site_port(site: str, configured_port: int | None) -> int | None:
    if configured_port:
        return int(configured_port)

    if ":" in site:
        maybe_port = site.rsplit(":", 1)[-1]
        if maybe_port.isdigit():
            return int(maybe_port)

    return None


def resolve_site_credentials(config: dict, site: str) -> SiteCredentials:
    raw_creds = config.get("site_credentials", {})
    if isinstance(raw_creds, dict) and site in raw_creds and isinstance(raw_creds[site], dict):
        creds = raw_creds[site]
        return SiteCredentials(
            api_key=creds.get("api_key", ""),
            api_secret=creds.get("api_secret", ""),
            port=parse_site_port(site, creds.get("port")),
            admin_user=creds.get("admin_user", "Administrator"),
            admin_password=creds.get("admin_password", ""),
        )

    return SiteCredentials(
        api_key=config.get("api_key", ""),
        api_secret=config.get("api_secret", ""),
        port=parse_site_port(site, config.get("site_port") or config.get("port")),
        admin_user=config.get("admin_user", "Administrator"),
        admin_password=config.get("admin_password", ""),
    )


def resolve_context(project_path: str, bench_id: str = "", site: str = "") -> BenchContext:
    config = load_frappe_config(project_path)
    bench_path = detect_bench_path(project_path, config)
    resolved_bench_id = (bench_id or str(config.get("bench_id", "")).strip() or bench_path.name).strip()
    resolved_site = (site or str(config.get("site", "")).strip()).strip()

    return BenchContext(
        project_path=project_path,
        bench_id=resolved_bench_id,
        bench_path=bench_path,
        bench_cmd=guess_bench_cmd(bench_path, config),
        node_version=str(config.get("node_version")).strip() if config.get("node_version") else None,
        site=resolved_site,
        site_credentials=resolve_site_credentials(config, resolved_site) if resolved_site else SiteCredentials(),
        config=config,
    )


def validate_bench_id(bench_id: str) -> str | None:
    if not bench_id:
        return "bench_id resolve nahi ho saka. .mcp-config.json me bench_id set karo ya tool me pass karo."
    if "/" in bench_id or "\\" in bench_id or ".." in bench_id:
        return f"Invalid bench_id '{bench_id}'."
    return None


def validate_site(site: str) -> str | None:
    if not site:
        return "site required hai. .mcp-config.json me site set karo ya tool me pass karo."
    if "/" in site or "\\" in site or ".." in site or not SITE_RE.match(site):
        return f"Invalid site '{site}'."
    return None


def validate_api_credentials(ctx: BenchContext) -> str | None:
    if not ctx.site_credentials.api_key or not ctx.site_credentials.api_secret:
        return (
            f"API credentials missing for site '{ctx.site}'. "
            "Set api_key/api_secret ya site_credentials in .mcp-config.json."
        )
    if not ctx.site_credentials.port:
        return (
            f"Port missing for site '{ctx.site}'. "
            "Set site_port ya site_credentials.<site>.port in .mcp-config.json."
        )
    return None


def validate_bench_command(ctx: BenchContext, command_parts: list[str]) -> str | None:
    blocked = ctx.config.get("blocked_commands", DEFAULT_BLOCKED_COMMANDS)
    joined = " ".join(command_parts).lower()
    for token in blocked:
        if str(token).lower() in joined:
            return f"Command blocked by security policy: contains '{token}'."
    return None


def scan_expression(ctx: BenchContext, expression: str) -> dict:
    expr_lower = expression.lower()
    blocked = {str(token).lower() for token in ctx.config.get("blocked_expressions", DEFAULT_BLOCKED_EXPRESSIONS)}
    blocked.update(DEFAULT_BLOCKED_EXPRESSIONS)

    for token in blocked:
        if token in expr_lower:
            return {
                "blocked": True,
                "block_reason": f"Expression contains blocked pattern '{token}'.",
            }

    warnings = []
    for token in ctx.config.get("warn_before_execute", DEFAULT_WARN_EXPRESSIONS):
        if str(token).lower() in expr_lower:
            warnings.append(str(token))

    if warnings:
        return {
            "blocked": False,
            "warning": f"Expression may modify data: {warnings}",
        }

    return {"blocked": False}


def extract_docker_container(bench_cmd: str) -> str | None:
    parts = shlex.split(bench_cmd)
    if not parts or parts[0] != "docker":
        return None
    try:
        exec_idx = parts.index("exec")
    except ValueError:
        return None

    flags_with_value = {"-w", "--workdir", "-u", "--user", "-e", "--env", "--entrypoint"}
    i = exec_idx + 1
    while i < len(parts):
        token = parts[i]
        if token.startswith("-"):
            i += 2 if token in flags_with_value else 1
        else:
            return token
    return None


def extract_docker_workdir(bench_cmd: str) -> str | None:
    parts = shlex.split(bench_cmd)
    for index, token in enumerate(parts):
        if token in {"-w", "--workdir"} and index + 1 < len(parts):
            return parts[index + 1]
    return None


def build_bench_cmd(ctx: BenchContext, subargs: list[str]) -> list[str]:
    base_parts = shlex.split(ctx.bench_cmd)

    if not ctx.node_version:
        return base_parts + subargs

    container = extract_docker_container(ctx.bench_cmd)
    if not container or not base_parts or base_parts[-1] != "bench":
        return base_parts + subargs

    docker_parts = base_parts[:-1]
    sub_cmd = shlex.join(["bench", *subargs])
    nvm_cmd = (
        'export NVM_DIR="$HOME/.nvm" && '
        '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && '
        f'nvm use {ctx.node_version} > /dev/null 2>&1 && '
        f"{sub_cmd}"
    )
    return docker_parts + ["bash", "-c", nvm_cmd]


def summarize_output(stdout: str = "", stderr: str = "", max_lines: int = 20) -> dict:
    lines = []
    if stdout:
        lines.extend(stdout.splitlines())
    if stderr:
        lines.extend(stderr.splitlines())

    total = len(lines)
    tail_lines = lines[-max_lines:]
    output = "\n".join(tail_lines).strip() or None
    last_error = next((line.strip() for line in reversed(stderr.splitlines()) if line.strip()), "")

    return {
        "output": output,
        "output_truncated": total > len(tail_lines),
        "total_output_lines": total,
        "returned_output_lines": len(tail_lines),
        "last_error_line": last_error,
    }


def ensure_bench_running(ctx: BenchContext) -> dict | None:
    container = extract_docker_container(ctx.bench_cmd)
    if not container:
        return None

    cache_key = f"{ctx.bench_id}:{container}"
    cached = BENCH_RUNNING_CACHE.get(cache_key)
    if cached and time.time() < cached[1]:
        return None if cached[0] else {
            "error": f"Docker container '{container}' is not running (cached).",
            "hint": f"Run: docker start {container}",
        }

    try:
        check = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Running}}", container],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        return {"error": "docker command not found on host."}
    except subprocess.TimeoutExpired:
        return {"error": f"Docker container '{container}' check timed out."}
    except Exception as exc:
        return {"error": f"Docker inspect failed: {exc}"}

    if check.returncode != 0:
        BENCH_RUNNING_CACHE[cache_key] = (False, time.time() + 10)
        return {
            "error": f"Docker container '{container}' nahi mila.",
            "hint": "docker ps / docker start check karo.",
        }

    if check.stdout.strip() == "true":
        BENCH_RUNNING_CACHE[cache_key] = (True, time.time() + BENCH_CACHE_TTL)
        return None

    start = subprocess.run(
        ["docker", "start", container],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if start.returncode != 0:
        BENCH_RUNNING_CACHE[cache_key] = (False, time.time() + 10)
        return {
            "error": f"Container '{container}' start nahi ho saka: {start.stderr.strip() or start.stdout.strip()}",
            "hint": f"Run: docker start {container}",
        }

    time.sleep(3)
    BENCH_RUNNING_CACHE[cache_key] = (True, time.time() + BENCH_CACHE_TTL)
    return None


def run_bench(ctx: BenchContext, subargs: list[str], timeout: int, cwd: str | None = None) -> subprocess.CompletedProcess:
    cmd = build_bench_cmd(ctx, subargs)
    blocked = validate_bench_command(ctx, cmd)
    if blocked:
        raise ValueError(blocked)

    return subprocess.run(
        cmd,
        cwd=cwd or str(ctx.bench_path),
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False,
    )


def ping_site(site: str, port: int | None) -> str:
    if not port:
        return "unknown"

    try:
        response = requests.get(
            f"http://localhost:{port}",
            headers={"Host": site},
            timeout=3,
            allow_redirects=True,
        )
    except Exception:
        return "stopped"

    return "running" if response.status_code < 500 else "stopped"


def discover_sites(bench_path: Path) -> list[str]:
    sites_dir = bench_path / "sites"
    if not sites_dir.is_dir():
        return []

    sites = []
    for entry in sorted(sites_dir.iterdir()):
        if entry.name in EXCLUDED_SITE_DIRS or not entry.is_dir():
            continue
        if not (entry / "site_config.json").is_file():
            continue
        if SITE_RE.match(entry.name):
            sites.append(entry.name)
    return sites


def read_site_config(bench_path: Path, site: str) -> dict:
    path = bench_path / "sites" / site / "site_config.json"
    if not path.exists():
        return {}

    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def read_common_site_config(bench_path: Path) -> dict:
    path = bench_path / "sites" / "common_site_config.json"
    if not path.exists():
        return {}

    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def get_site_port(ctx: BenchContext, site: str) -> int | None:
    if site == ctx.site and ctx.site_credentials.port:
        return ctx.site_credentials.port

    raw_creds = ctx.config.get("site_credentials", {})
    if isinstance(raw_creds, dict) and site in raw_creds and isinstance(raw_creds[site], dict):
        return parse_site_port(site, raw_creds[site].get("port"))

    common_site_config = read_common_site_config(ctx.bench_path)
    if common_site_config.get("webserver_port"):
        try:
            return int(common_site_config["webserver_port"])
        except Exception:
            pass

    return parse_site_port(site, ctx.config.get("site_port") or ctx.config.get("port"))


def get_installed_apps(ctx: BenchContext, site: str) -> list[str]:
    try:
        result = run_bench(ctx, ["--site", site, "list-apps"], timeout=20)
    except Exception:
        return []

    if result.returncode != 0 or not result.stdout.strip():
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def try_parse_output(raw: str) -> Any:
    try:
        return ast.literal_eval(raw)
    except Exception:
        return raw


def build_execute_method(expression: str) -> str:
    wrapped = f"""
try:
    _mcp_result = eval(compile({json.dumps(expression)}, "<bench execute>", "eval"), globals(), locals())
except SyntaxError:
    exec(compile({json.dumps(expression)}, "<bench execute>", "exec"), globals(), locals())
"""
    return (
        '(lambda _mcp_ns={}: '
        '(__import__("builtins").exec(compile('
        + json.dumps(wrapped)
        + ', "<mcp wrapper>", "exec"), globals(), _mcp_ns), '
        '_mcp_ns.get("_mcp_result"))[1])()'
    )


def background_start_command(ctx: BenchContext) -> tuple[list[str], str]:
    container = extract_docker_container(ctx.bench_cmd)
    workdir = extract_docker_workdir(ctx.bench_cmd)
    log_file = f"/tmp/{ctx.bench_id}-start.log"

    nvm_part = ""
    if ctx.node_version:
        nvm_part = (
            'export NVM_DIR="$HOME/.nvm" && '
            '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && '
            f'nvm use {ctx.node_version} > /dev/null 2>&1 && '
        )

    start_cmd = f"{nvm_part}nohup bench start > {log_file} 2>&1 &"

    if container:
        cmd = ["docker", "exec"]
        if workdir:
            cmd += ["-w", workdir]
        cmd += [container, "bash", "-l", "-c", start_cmd]
        return cmd, log_file

    bench_shell = shlex.quote(ctx.bench_cmd)
    host_cmd = ["bash", "-lc", f"{nvm_part}nohup {bench_shell} start > {log_file} 2>&1 &"]
    return host_cmd, log_file


def resolve_log_path(bench_path: Path, log_type: str, site: str) -> Path:
    if log_type == "bench":
        return bench_path / "logs" / "bench.log"
    mapping = {
        "error": "web.error.log",
        "scheduler": "scheduler.log",
        "worker": "worker.log",
        "web": "web.log",
    }
    return bench_path / "sites" / site / "logs" / mapping[log_type]


def classify_log_line(line: str) -> str:
    lower = line.lower()
    if any(token in lower for token in ("critical", "fatal")):
        return "CRITICAL"
    if any(token in lower for token in ("error", "exception", "traceback", "errno")):
        return "ERROR"
    if any(token in lower for token in ("warning", "warn", "deprecated")):
        return "WARNING"
    return "INFO"


def parse_timestamp(line: str):
    from datetime import datetime

    formats = [
        "%Y-%m-%d %H:%M:%S,%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%d-%b-%Y %H:%M:%S",
    ]

    segment = line[:30].strip()
    for fmt in formats:
        try:
            return datetime.strptime(segment[:len(fmt)], fmt)
        except ValueError:
            continue
    return None
