import json
import os
import time
from pathlib import Path
from config import load_project_config, save_project_config
from core.project_detector import detect_framework, format_detection_message

# Cache: project_path → (detected_framework, timestamp)
_detection_cache: dict[str, tuple[str, float]] = {}
_CACHE_TTL = 60  # seconds


def check_framework_switch(project_path: str) -> str | None:
    """
    Compare saved config framework vs freshly detected framework.
    Returns a warning string if mismatch found, else None.
    Caches detection result for 60s to avoid repeated disk scans.
    """
    cfg = load_project_config(project_path)
    saved_fw = (cfg.get("framework") or "").lower().strip() if cfg else ""

    # Use cache if fresh
    now = time.time()
    if project_path in _detection_cache:
        detected_fw, ts = _detection_cache[project_path]
        if now - ts < _CACHE_TTL:
            return _build_switch_warning(project_path, saved_fw, detected_fw)

    results = detect_framework(project_path)
    detected_fw = results[0]["framework"] if results else "unknown"
    _detection_cache[project_path] = (detected_fw, now)

    return _build_switch_warning(project_path, saved_fw, detected_fw)


def _build_switch_warning(project_path: str, saved_fw: str, detected_fw: str) -> str | None:
    if not saved_fw or saved_fw == "generic":
        # No saved config — suggest running project_context first
        if detected_fw and detected_fw != "unknown":
            return (
                f"⚠️ FRAMEWORK SWITCH DETECTED\n"
                f"Path: {project_path}\n"
                f"Detected: {detected_fw.upper()} — lekin .mcp-config.json nahi hai.\n"
                f"Pehle `project_context` tool call karo taaki AI sahi context load kare."
            )
        return None

    if detected_fw and detected_fw != "unknown" and detected_fw != saved_fw:
        return (
            f"⚠️ FRAMEWORK MISMATCH\n"
            f"Saved config: {saved_fw.upper()}\n"
            f"Detected now: {detected_fw.upper()}\n"
            f"Path: {project_path}\n\n"
            f"Lagta hai aap ek naye project par switch kar rahe ho.\n"
            f"`project_context` tool call karo nayi project ka context load karne ke liye,\n"
            f"ya `confirm_framework(framework='{detected_fw}')` se update karo."
        )
    return None

COMMON_CONFIG_KEYS = {
    "framework",
    "project_path",
    "detected_by",
    "language",
    "db",
    "run_command",
    "test_command",
    "env_file",
    "allowed_tools",
}


def get_project_context(project_path: str) -> str:
    """
    Main tool: Read .mcp-config.json if exists, else trigger hybrid detection.
    Returns a rich context string for Claude.
    """
    cfg = load_project_config(project_path)

    if cfg:
        return _format_existing_config(project_path, cfg)
    else:
        return (
            "⚠️ .mcp-config.json nahi mili is project mein.\n\n"
            + format_detection_message(project_path)
            + "\n\nConfirm karne ke baad main config save kar dunga."
        )


def confirm_framework(project_path: str, framework: str, extra: dict = None) -> str:
    """Save .mcp-config.json after developer confirms framework."""
    framework = framework.lower().strip()
    config = {
        "framework": framework,
        "project_path": project_path,
        "detected_by": "universal-dev-mcp",
    }
    if extra:
        framework_payload = {}
        for key, value in extra.items():
            if key in COMMON_CONFIG_KEYS:
                config[key] = value
            else:
                framework_payload[key] = value
        if framework_payload:
            config[framework] = framework_payload

    save_project_config(project_path, config)
    return (
        f"✅ .mcp-config.json saved!\n\n"
        f"Framework: {framework}\n"
        f"Project: {project_path}\n\n"
        f"Ab main is project ke liye sahi tools use karunga.\n"
        f"Aap kya karna chahte hain?"
    )


def _format_existing_config(project_path: str, cfg: dict) -> str:
    framework = cfg.get("framework", "unknown")
    lines = [
        f"📁 Project Context Loaded",
        f"",
        f"Active Path: {project_path}",
        f"Framework:   {framework.upper()}",
    ]

    common_keys = ["language", "db", "run_command", "test_command", "env_file", "allowed_tools"]
    for key in common_keys:
        if key in cfg:
            lines.append(f"{key.capitalize()}: {cfg[key]}")

    framework_specific = {
        key: val for key, val in cfg.items()
        if key not in COMMON_CONFIG_KEYS
    }
    if framework_specific:
        lines.append(f"{framework.capitalize()} Config: {framework_specific}")

    lines += ["", "Kya karna chahte hain?"]
    return "\n".join(lines)
