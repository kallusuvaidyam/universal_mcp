import json
import re
from typing import Any, Dict, List, Optional

from core import memory_manager
from core.project_context import get_project_context


def _extract_keywords(text: str) -> List[str]:
    text = (text or "").lower()
    # simple tokenizer
    tokens = re.split(r"[^a-z0-9_]+", text)
    tokens = [t for t in tokens if t and len(t) >= 2]
    # de-dup while preserving order
    seen = set()
    out = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out[:30]


def generate_plan(
    project_path: str,
    user_id: str,
    request_text: str,
    framework_hint: Optional[str] = None,
) -> str:
    """Generate a structured plan using project context + memories.

    Returns a JSON string so Claude can follow deterministically.
    """

    keywords = _extract_keywords(request_text)

    project_context = get_project_context(project_path)

    # Pull some memories (best-effort). These tools exist only in our core module.
    # If nothing exists yet, functions return friendly strings.
    decision_hits = memory_manager.decision_memory_search(
        project_path=project_path,
        user_id=user_id,
        query=request_text,
        limit=5,
    )

    debug_hits = memory_manager.debug_memory_list(
        project_path=project_path,
        user_id=user_id,
        scope=None,
        limit=10,
    )

    semantic_hits = memory_manager.semantic_memory_search(
        project_path=project_path,
        user_id=user_id,
        query=request_text,
        limit=5,
    )

    # Heuristic steps
    steps: List[Dict[str, Any]] = []

    # 1) Quick context + config check
    steps.append(
        {
            "title": "Confirm project context",
            "actions": [
                {
                    "type": "tool",
                    "tool": "project_context",
                    "input": {},
                }
            ],
            "notes": "Use .mcp-config.json if available; otherwise rely on scan hints from get_project_context().",
        }
    )

    # 2) Check memories to select approach
    steps.append(
        {
            "title": "Use existing memories to choose approach",
            "actions": [
                {
                    "type": "analysis",
                    "inputs": {
                        "decision_memory": decision_hits,
                        "debug_memory": debug_hits,
                        "semantic_memory": semantic_hits,
                        "keywords": keywords,
                        "framework_hint": framework_hint,
                    },
                }
            ],
            "notes": "Match request keywords to semantic memory; reuse past decisions/debug fixes.",
        }
    )

    # 3) Execute: prefer smallest safe action
    steps.append(
        {
            "title": "Execute minimal safe actions",
            "actions": [
                {
                    "type": "tool",
                    "tool": "file_search",
                    "input": {
                        "pattern": keywords[0] if keywords else request_text[:20],
                        "file_pattern": "*",
                    },
                }
            ],
            "notes": "Then iteratively refine using file_read/shell_run based on findings.",
        }
    )

    # 4) Store decision/debug after each iteration
    steps.append(
        {
            "title": "Persist learnings",
            "actions": [
                {
                    "type": "tool",
                    "tool": "decision_memory_add",
                    "input": {
                        "decision_id": "auto",
                        "decision_text": "(fill after deciding)",
                        "metadata_json": json.dumps({"request": request_text[:200]}),
                    },
                },
                {
                    "type": "tool",
                    "tool": "debug_memory_add",
                    "input": {
                        "scope": "agent_planner",
                        "error_text": "(fill if an error occurred)",
                        "context_text": "(fill with tool output summary)",
                        "metadata_json": "{}",
                    },
                },
            ],
            "notes": "After success, also store semantic snippet summarizing the fix.",
        }
    )

    result = {
        "project_path": project_path,
        "user_id": user_id,
        "request": request_text,
        "framework_hint": framework_hint,
        "project_context_snapshot": project_context,
        "plan": {
            "steps": steps,
        },
    }

    return json.dumps(result, ensure_ascii=False, indent=2)

