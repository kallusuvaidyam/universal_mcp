import os
import signal
import subprocess
from pathlib import Path

from plugins.shared import collect_files, run_command, summarize_paths

_PID_FILE = Path("/tmp/flutter_run.pid")
_LOG_FILE = Path("/tmp/flutter_run.log")


def flutter_pub_get(project_path: str) -> str:
    return run_command("flutter pub get", project_path, timeout=240)


def flutter_test(project_path: str) -> str:
    return run_command("flutter test", project_path, timeout=300)


def flutter_analyze(project_path: str) -> str:
    return run_command("flutter analyze", project_path, timeout=300)


def flutter_build_apk(project_path: str) -> str:
    return run_command("flutter build apk", project_path, timeout=600)


def flutter_list_screens(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.dart",),
        path_terms=("lib/screens/", "lib/screen/", "lib/pages/", "lib/views/"),
        limit=80,
    )
    if files:
        return summarize_paths("Flutter screen files:", files, "No Flutter screen files found.")

    root = Path(project_path)
    if not (root / "lib").is_dir():
        return "No lib/ directory found."

    fallback = collect_files(
        project_path,
        patterns=("*.dart",),
        path_terms=("lib/",),
        name_terms=("screen", "page", "view"),
        limit=80,
    )
    return summarize_paths("Flutter screen-like files:", fallback, "No Flutter screen files found.")


def flutter_run(project_path: str, device: str = "linux") -> str:
    if _PID_FILE.exists():
        try:
            pid = int(_PID_FILE.read_text().strip())
            os.kill(pid, 0)
            return f"Flutter already running (PID {pid}). Use flutter_stop first. Logs: {_LOG_FILE}"
        except (ProcessLookupError, ValueError):
            _PID_FILE.unlink(missing_ok=True)

    root = Path(project_path)
    if not root.exists():
        return f"ERROR: Project path not found: {project_path}"

    _LOG_FILE.write_text("")
    with open(_LOG_FILE, "w") as log:
        proc = subprocess.Popen(
            ["flutter", "run", "-d", device],
            cwd=root,
            stdout=log,
            stderr=log,
            start_new_session=True,
        )

    _PID_FILE.write_text(str(proc.pid))
    return f"Flutter app started on '{device}' (PID {proc.pid}). Logs: {_LOG_FILE}"


def flutter_stop(project_path: str) -> str:
    if not _PID_FILE.exists():
        return "No running Flutter process found."

    try:
        pid = int(_PID_FILE.read_text().strip())
        os.killpg(os.getpgid(pid), signal.SIGTERM)
        _PID_FILE.unlink(missing_ok=True)
        return f"Flutter process (PID {pid}) stopped."
    except (ProcessLookupError, ValueError):
        _PID_FILE.unlink(missing_ok=True)
        return "Flutter process was not running (cleaned up stale PID)."
    except Exception as e:
        return f"ERROR stopping Flutter: {e}"


def flutter_logs(project_path: str, lines: int = 50) -> str:
    if not _LOG_FILE.exists():
        return "No Flutter log file found. Start the app with flutter_run first."
    try:
        content = _LOG_FILE.read_text(errors="ignore")
        all_lines = content.splitlines()
        tail = all_lines[-lines:] if len(all_lines) > lines else all_lines
        return "\n".join(tail) or "(No output yet)"
    except Exception as e:
        return f"ERROR reading logs: {e}"


TOOLS = {
    "flutter_pub_get": {"fn": flutter_pub_get, "description": "Run flutter pub get"},
    "flutter_test": {"fn": flutter_test, "description": "Run Flutter tests"},
    "flutter_analyze": {"fn": flutter_analyze, "description": "Run flutter analyze"},
    "flutter_build_apk": {"fn": flutter_build_apk, "description": "Build Flutter Android APK"},
    "flutter_list_screens": {"fn": flutter_list_screens, "description": "List Flutter screen files"},
    "flutter_run": {"fn": flutter_run, "description": "Run Flutter app in background on a device (linux/chrome/android device ID)"},
    "flutter_stop": {"fn": flutter_stop, "description": "Stop the running Flutter app"},
    "flutter_logs": {"fn": flutter_logs, "description": "Show recent Flutter run logs (last N lines, default 50)"},
}
