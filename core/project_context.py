import json
import os
from pathlib import Path
from config import load_project_config, save_project_config
from core.project_detector import detect_framework, format_detection_message

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
        f"Path:      {project_path}",
        f"Framework: {framework.upper()}",
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
