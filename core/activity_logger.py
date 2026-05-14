"""Multi-developer activity log. Stored in ~/.universal-dev-mcp/memory.db."""
import json
import sqlite3
import subprocess
import time
from datetime import datetime
from pathlib import Path

_DB_PATH = str(Path.home() / ".universal-dev-mcp" / "memory.db")


def _conn():
    db = sqlite3.connect(_DB_PATH)
    db.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT NOT NULL,
            developer TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            summary TEXT,
            branch TEXT,
            extra_json TEXT,
            created_at REAL NOT NULL
        )
    """)
    db.commit()
    return db


def _get_branch(project_path: str) -> str:
    try:
        r = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=project_path, capture_output=True, text=True, timeout=5
        )
        return r.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def log_activity(project: str, developer: str, tool_name: str, summary: str = "", extra: dict = None):
    """Log a developer action. Called automatically by server.py tool handlers."""
    try:
        branch = _get_branch(project)
        db = _conn()
        db.execute(
            "INSERT INTO activity_log (project,developer,tool_name,summary,branch,extra_json,created_at) VALUES (?,?,?,?,?,?,?)",
            (project, developer, tool_name, summary, branch, json.dumps(extra or {}), time.time())
        )
        db.commit()
        db.close()
    except Exception:
        pass  # never break tool calls due to logging failure


def get_activity_log(project: str, developer: str = None, branch: str = None, since: str = "24h", limit: int = 50) -> str:
    """Query and format activity log for a project."""
    _SINCE_MAP = {"today": 86400, "1h": 3600, "24h": 86400, "7d": 604800, "all": None}
    seconds = _SINCE_MAP.get(since, 86400)
    since_ts = time.time() - seconds if seconds is not None else 0

    try:
        db = _conn()
        query = "SELECT developer,tool_name,summary,branch,created_at FROM activity_log WHERE project=? AND created_at>=?"
        params = [project, since_ts]
        if developer:
            query += " AND developer=?"
            params.append(developer)
        if branch:
            query += " AND branch=?"
            params.append(branch)
        query += " ORDER BY created_at ASC LIMIT ?"
        params.append(limit)
        rows = db.execute(query, params).fetchall()
        db.close()
    except Exception as e:
        return f"Error reading activity log: {e}"

    if not rows:
        return f"📋 Koi activity nahi mili (since: {since}, developer: {developer or 'all'})"

    proj_name = Path(project).name
    lines = [f"📋 Activity Log (last {since}) — {proj_name}\n"]
    for dev, tool, summary, br, ts in rows:
        dt = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
        lines.append(f"[{dt}] {dev:<12} [{br:<12}]  {tool:<22} → {summary}")
    return "\n".join(lines)
