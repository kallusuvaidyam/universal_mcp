import json
import os
import signal
import subprocess
import time
from pathlib import Path

from config import GLOBAL_CONFIG_DIR
from core.shell_executor import BLOCKED_COMMANDS

_SERVICES_DIR = GLOBAL_CONFIG_DIR / "services"
_REGISTRY_FILE = _SERVICES_DIR / "registry.json"


def _load_registry() -> dict:
    if _REGISTRY_FILE.exists():
        try:
            return json.loads(_REGISTRY_FILE.read_text())
        except Exception:
            return {}
    return {}


def _save_registry(registry: dict):
    _SERVICES_DIR.mkdir(parents=True, exist_ok=True)
    _REGISTRY_FILE.write_text(json.dumps(registry, indent=2))


def _is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def service_run(project_path: str, name: str, command: str) -> str:
    """Start a long-running command as a detached background process."""
    cmd_lower = command.lower()
    for blocked in BLOCKED_COMMANDS:
        if blocked in cmd_lower:
            return f"❌ Blocked: '{blocked}' is not allowed for safety."

    registry = _load_registry()
    existing = registry.get(name)
    if existing and _is_alive(existing["pid"]):
        return f"❌ Service '{name}' already running (pid {existing['pid']}). Use service_restart or service_stop first."

    _SERVICES_DIR.mkdir(parents=True, exist_ok=True)
    log_path = str(_SERVICES_DIR / f"{name}.log")
    try:
        log_file = open(log_path, "w")
        proc = subprocess.Popen(
            command,
            shell=True,
            cwd=project_path,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    except Exception as e:
        return f"❌ Error starting service: {e}"

    registry[name] = {
        "pid": proc.pid,
        "command": command,
        "log": log_path,
        "project": project_path,
        "started_at": time.time(),
    }
    _save_registry(registry)
    return f"✅ Service '{name}' started (pid {proc.pid}).\nLog: {log_path}\nUse service_logs(name='{name}') to see output."


def service_logs(project_path: str, name: str = "", n: int = 50) -> str:
    """Tail a service's log, or list all services if no name given."""
    registry = _load_registry()

    if not name:
        if not registry:
            return "No services tracked. Start one with service_run."
        lines = ["Tracked services:"]
        for svc_name, info in registry.items():
            status = "🟢 running" if _is_alive(info["pid"]) else "⚪ stopped"
            lines.append(f"  {svc_name:20} {status:12} pid {info['pid']}  {info['command'][:50]}")
        return "\n".join(lines)

    info = registry.get(name)
    if not info:
        return f"❌ No such service: {name}"
    log_path = Path(info["log"])
    if not log_path.exists():
        return f"❌ Log not found for '{name}': {log_path}"
    try:
        tail = log_path.read_text(errors="replace").splitlines()[-n:]
        status = "🟢 running" if _is_alive(info["pid"]) else "⚪ stopped"
        return f"[{name}] {status} (pid {info['pid']}) — last {n} lines:\n\n" + "\n".join(tail)
    except Exception as e:
        return f"❌ Error reading log: {e}"


def service_stop(project_path: str, name: str) -> str:
    """Stop a managed service (SIGTERM then SIGKILL) and drop it from the registry."""
    registry = _load_registry()
    info = registry.get(name)
    if not info:
        return f"❌ No such service: {name}"

    pid = info["pid"]
    if _is_alive(pid):
        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
            for _ in range(20):
                if not _is_alive(pid):
                    break
                time.sleep(0.1)
            if _is_alive(pid):
                os.killpg(os.getpgid(pid), signal.SIGKILL)
        except Exception as e:
            return f"❌ Error stopping '{name}': {e}"

    del registry[name]
    _save_registry(registry)
    return f"✅ Service '{name}' stopped (pid {pid})."


def service_restart(project_path: str, name: str) -> str:
    """Stop then re-start a managed service using its stored command."""
    registry = _load_registry()
    info = registry.get(name)
    if not info:
        return f"❌ No such service: {name}"
    command = info["command"]
    project = info.get("project", project_path)
    service_stop(project_path, name)
    return service_run(project, name, command)
