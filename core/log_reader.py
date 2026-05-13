from pathlib import Path
from core.file_manager import _safe_path


def log_tail(project_path: str, log_path: str, n: int = 50) -> str:
    """Read last N lines of any log file."""
    target = _safe_path(project_path, log_path)
    if not target:
        return "❌ Access denied."
    if not target.exists():
        return f"❌ Log file not found: {log_path}"

    try:
        lines = target.read_text(errors="replace").splitlines()
        tail = lines[-n:] if len(lines) > n else lines
        return f"[Last {len(tail)} lines of {log_path}]\n\n" + "\n".join(tail)
    except Exception as e:
        return f"❌ Error reading log: {e}"


def log_grep(project_path: str, log_path: str, pattern: str, n: int = 50) -> str:
    """Search for a pattern in a log file and return matching lines."""
    target = _safe_path(project_path, log_path)
    if not target or not target.exists():
        return f"❌ Log file not found: {log_path}"

    try:
        lines = target.read_text(errors="replace").splitlines()
        matches = [l for l in lines if pattern.lower() in l.lower()]
        matches = matches[-n:]
        if not matches:
            return f"No lines matching '{pattern}' found in {log_path}"
        return f"[{len(matches)} matches for '{pattern}' in {log_path}]\n\n" + "\n".join(matches)
    except Exception as e:
        return f"❌ Error: {e}"
