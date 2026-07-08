import os
import subprocess
from pathlib import Path

from config import load_project_config

_WRITE_KEYWORDS = [
    "insert", "update", "delete", "drop", "truncate", "alter",
    "create", "replace", "grant", "revoke",
]


def _read_env(project_path: str, env_file: str = ".env") -> dict:
    env = {}
    path = Path(project_path) / env_file
    if not path.exists():
        return env
    for line in path.read_text(errors="replace").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            key, _, val = line.partition("=")
            env[key.strip().upper()] = val.strip().strip('"').strip("'")
    return env


def _resolve_conn(project_path: str) -> dict:
    cfg = load_project_config(project_path)
    env = _read_env(project_path)
    return {
        "type": (cfg.get("db_type") or cfg.get("db") or env.get("DB_TYPE") or "mysql").lower(),
        "host": cfg.get("db_host") or env.get("DB_HOST") or "127.0.0.1",
        "port": str(cfg.get("db_port") or env.get("DB_PORT") or ""),
        "user": cfg.get("db_user") or env.get("DB_USER") or env.get("DB_USERNAME") or "root",
        "password": cfg.get("db_password") or env.get("DB_PASSWORD") or "",
        "name": cfg.get("db_name") or env.get("DB_NAME") or env.get("DB_DATABASE") or "",
    }


def db_query(project_path: str, query: str, confirm: bool = False) -> str:
    """Run a read-only SQL query against the project DB. Writes require confirm=True."""
    q_lower = query.strip().lower()
    if not confirm and any(q_lower.startswith(kw) or f" {kw} " in q_lower for kw in _WRITE_KEYWORDS):
        return (
            "⚠️ This looks like a write/DDL query and is blocked by default.\n"
            "If you really mean it, re-call with confirm=True."
        )

    conn = _resolve_conn(project_path)
    db_type = conn["type"]

    if "postgres" in db_type or db_type == "psql":
        cmd = ["psql", "-h", conn["host"], "-U", conn["user"], "-d", conn["name"], "-c", query]
        if conn["port"]:
            cmd[1:1] = ["-p", conn["port"]]
        run_env = {**os.environ, "PGPASSWORD": conn["password"]}
    else:
        cmd = ["mysql", "-h", conn["host"], "-u", conn["user"]]
        if conn["port"]:
            cmd += ["-P", conn["port"]]
        if conn["name"]:
            cmd += ["-D", conn["name"]]
        cmd += ["-e", query]
        run_env = {**os.environ, "MYSQL_PWD": conn["password"]}

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=run_env)
        out = (result.stdout + result.stderr).strip()
        return out or "(No output)"
    except FileNotFoundError:
        return f"❌ DB client not found for type '{db_type}'. Install the mysql/psql CLI."
    except Exception as e:
        return f"❌ DB error: {e}"
