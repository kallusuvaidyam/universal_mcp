import sqlite3
import time
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import GLOBAL_CONFIG_DIR

DB_PATH = GLOBAL_CONFIG_DIR / "memory.db"


def _get_conn():
    GLOBAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT,
            key TEXT,
            value TEXT,
            created_at REAL
        )
    """
    )

    # Project Memory: who works on what + key/value notes
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS project_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT,
            user_id TEXT,
            key TEXT,
            value TEXT,
            created_at REAL,
            updated_at REAL
        )
    """
    )

    # Decision Memory: assistant decisions + reasons
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS decision_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT,
            user_id TEXT,
            decision_id TEXT,
            decision_text TEXT,
            metadata_json TEXT,
            created_at REAL
        )
    """
    )

    # Debug Memory: errors and troubleshooting context
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS debug_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT,
            user_id TEXT,
            scope TEXT,
            error_text TEXT,
            context_text TEXT,
            metadata_json TEXT,
            created_at REAL
        )
    """
    )

    # Semantic Memory: tag->text snippets (keyword overlap search)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS semantic_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT,
            user_id TEXT,
            tag TEXT,
            text TEXT,
            metadata_json TEXT,
            created_at REAL
        )
    """
    )

    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_memory_pk ON memory(project, key)")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_project_memory_pk ON project_memory(project, user_id, key)")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.commit()
    return conn



def memory_save(project_path: str, key: str, value: str) -> str:
    conn = _get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO memory (project, key, value, created_at) VALUES (?,?,?,?)",
        (project_path, key, value, time.time())
    )
    conn.commit()
    conn.close()
    return f"✅ Memory saved: [{key}]"


def memory_get(project_path: str, key: str) -> str:
    conn = _get_conn()
    row = conn.execute(
        "SELECT value FROM memory WHERE project=? AND key=?",
        (project_path, key)
    ).fetchone()
    conn.close()
    if row:
        return row[0]
    return f"❌ No memory found for key: {key}"


def memory_list(project_path: str) -> str:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT key, value FROM memory WHERE project=? ORDER BY created_at DESC",
        (project_path,)
    ).fetchall()
    conn.close()
    if not rows:
        return "No memories saved for this project."
    lines = [f"• {k}: {v[:100]}" for k, v in rows]
    return f"Saved memories ({len(rows)}):\n\n" + "\n".join(lines)


def memory_delete(project_path: str, key: str) -> str:
    conn = _get_conn()
    conn.execute("DELETE FROM memory WHERE project=? AND key=?", (project_path, key))
    conn.commit()
    conn.close()
    return f"✅ Memory deleted: [{key}]"


# ─────────────────────────────────────────────
# Project Memory (user <-> project notes)
# ─────────────────────────────────────────────

def project_memory_set(project_path: str, user_id: str, key: str, value: str) -> str:
    conn = _get_conn()
    now = time.time()
    # Upsert on (project,user_id,key)
    conn.execute(
        """
        INSERT INTO project_memory (project, user_id, key, value, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(project, user_id, key) DO UPDATE SET
            value=excluded.value,
            updated_at=excluded.updated_at
        """,
        (project_path, user_id, key, value, now, now),
    )
    conn.commit()
    conn.close()
    return f"✅ Project memory saved: [{key}]"


def project_memory_get(project_path: str, user_id: str, key: str) -> str:
    conn = _get_conn()
    row = conn.execute(
        """
        SELECT value
        FROM project_memory
        WHERE project=? AND user_id=? AND key=?
        ORDER BY updated_at DESC
        LIMIT 1
        """,
        (project_path, user_id, key),
    ).fetchone()
    conn.close()
    if row:
        return row[0]
    return f"❌ No project memory found for key: {key}"


def project_memory_list(project_path: str, user_id: str) -> str:
    conn = _get_conn()
    rows = conn.execute(
        """
        SELECT key, value
        FROM project_memory
        WHERE project=? AND user_id=?
        ORDER BY updated_at DESC
        """,
        (project_path, user_id),
    ).fetchall()
    conn.close()
    if not rows:
        return "No project memories saved for this user/project."
    lines = [f"• {k}: {v[:100]}" for k, v in rows]
    return f"Saved project memories ({len(rows)}):\n\n" + "\n".join(lines)


# ─────────────────────────────────────────────
# Decision Memory
# ─────────────────────────────────────────────

def decision_memory_add(
    project_path: str,
    user_id: str,
    decision_id: str,
    decision_text: str,
    metadata_json: str = "{}",
) -> str:
    conn = _get_conn()
    conn.execute(
        """
        INSERT INTO decision_memory (project, user_id, decision_id, decision_text, metadata_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (project_path, user_id, decision_id, decision_text, metadata_json, time.time()),
    )
    conn.commit()
    conn.close()
    return f"✅ Decision memory added: [{decision_id}]"


def _keyword_score(query: str, text: str) -> int:
    q = _extract_search_tokens(query)
    t = set(_extract_search_tokens(text))
    return sum(1 for token in q if token in t)


def _extract_search_tokens(text: str, max_tokens: int = 60) -> List[str]:
    import re

    text = (text or "").lower()
    tokens = re.split(r"[^a-z0-9_]+", text)
    tokens = [t for t in tokens if t and len(t) >= 3]
    # de-dup
    out = []
    seen = set()
    for tok in tokens:
        if tok not in seen:
            seen.add(tok)
            out.append(tok)
        if len(out) >= max_tokens:
            break
    return out


def decision_memory_search(
    project_path: str,
    user_id: str,
    query: str,
    limit: int = 5,
) -> str:
    conn = _get_conn()
    rows = conn.execute(
        """
        SELECT decision_id, decision_text, metadata_json
        FROM decision_memory
        WHERE project=? AND user_id=?
        """,
        (project_path, user_id),
    ).fetchall()
    conn.close()

    if not rows:
        return "No decision memories found."

    scored = []
    for decision_id, decision_text, metadata_json in rows:
        score = _keyword_score(query, f"{decision_id} {decision_text} {metadata_json}")
        if score > 0:
            scored.append((score, decision_id, decision_text, metadata_json))

    scored.sort(key=lambda x: x[0], reverse=True)
    scored = scored[: max(1, limit)]
    if not scored:
        # fallback: most recent
        recent = rows[:limit]
        lines = [f"• {did}: {dt[:140]}" for did, dt, _ in recent]
        return "(No keyword matches) Recent decisions:\n\n" + "\n".join(lines)

    lines = [f"• [{did}] (score={sc}) {dt[:160]}" for sc, did, dt, _ in scored]
    return f"Decision memory matches ({len(lines)}):\n\n" + "\n".join(lines)


# ─────────────────────────────────────────────
# Debug Memory
# ─────────────────────────────────────────────

def debug_memory_add(
    project_path: str,
    user_id: str,
    scope: str,
    error_text: str,
    context_text: str = "",
    metadata_json: str = "{}",
) -> str:
    conn = _get_conn()
    conn.execute(
        """
        INSERT INTO debug_memory (project, user_id, scope, error_text, context_text, metadata_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (project_path, user_id, scope, error_text, context_text, metadata_json, time.time()),
    )
    conn.commit()
    conn.close()
    return f"✅ Debug memory saved for scope: [{scope}]"


def debug_memory_list(
    project_path: str,
    user_id: str,
    scope: Optional[str] = None,
    limit: int = 50,
) -> str:
    conn = _get_conn()
    if scope:
        rows = conn.execute(
            """
            SELECT scope, error_text, context_text, created_at
            FROM debug_memory
            WHERE project=? AND user_id=? AND scope=?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (project_path, user_id, scope, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT scope, error_text, context_text, created_at
            FROM debug_memory
            WHERE project=? AND user_id=?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (project_path, user_id, limit),
        ).fetchall()

    conn.close()
    if not rows:
        return "No debug memories found."

    lines = [f"• ({sc}) {err[:140]}" for sc, err, _ctx, _t in rows]
    return f"Debug memories ({len(rows)}):\n\n" + "\n".join(lines)


# ─────────────────────────────────────────────
# Semantic Memory (tagged snippets + keyword overlap search)
# ─────────────────────────────────────────────

def semantic_memory_add(
    project_path: str,
    user_id: str,
    tag: str,
    text: str,
    metadata_json: str = "{}",
) -> str:
    conn = _get_conn()
    conn.execute(
        """
        INSERT INTO semantic_memory (project, user_id, tag, text, metadata_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (project_path, user_id, tag, text, metadata_json, time.time()),
    )
    conn.commit()
    conn.close()
    return f"✅ Semantic memory added: [{tag}]"


def semantic_memory_search(
    project_path: str,
    user_id: str,
    query: str,
    limit: int = 5,
) -> str:
    conn = _get_conn()
    rows = conn.execute(
        """
        SELECT tag, text, metadata_json
        FROM semantic_memory
        WHERE project=? AND user_id=?
        """,
        (project_path, user_id),
    ).fetchall()
    conn.close()

    if not rows:
        return "No semantic memories found."

    scored = []
    for tag, text, metadata_json in rows:
        score = _keyword_score(query, f"{tag} {text} {metadata_json}")
        if score > 0:
            scored.append((score, tag, text, metadata_json))

    scored.sort(key=lambda x: x[0], reverse=True)
    scored = scored[: max(1, limit)]

    if not scored:
        recent = rows[:limit]
        lines = [f"• {tag}: {txt[:140]}" for tag, txt, _ in recent]
        return "(No keyword matches) Recent semantic snippets:\n\n" + "\n".join(lines)

    lines = [f"• [{tag}] (score={sc}) {txt[:170]}" for sc, tag, txt, _ in scored]
    return f"Semantic memory matches ({len(lines)}):\n\n" + "\n".join(lines)

