import json
from pathlib import Path

GLOBAL_CONFIG_DIR = Path.home() / ".universal-dev-mcp"
GLOBAL_CONFIG_FILE = GLOBAL_CONFIG_DIR / "config.json"
COMMON_PROJECT_KEYS = {
    "_comment",
    "_note",
    "framework",
    "language",
    "db",
    "run_command",
    "test_command",
    "env_file",
    "allowed_tools",
    "project_path",
    "detected_by",
}


def load_global_config() -> dict:
    if GLOBAL_CONFIG_FILE.exists():
        return json.loads(GLOBAL_CONFIG_FILE.read_text())
    return {}


def save_global_config(config: dict):
    GLOBAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    GLOBAL_CONFIG_FILE.write_text(json.dumps(config, indent=2))


def _normalize_project_config(raw_config: dict) -> dict:
    if not isinstance(raw_config, dict):
        return {}

    normalized = dict(raw_config)
    framework = str(raw_config.get("framework", "")).strip().lower()
    framework_config = raw_config.get(framework, {}) if framework else {}

    if framework and isinstance(framework_config, dict):
        normalized.update(framework_config)

    return normalized


def _split_project_config(config: dict) -> dict:
    if not isinstance(config, dict):
        return {}

    framework = str(config.get("framework", "")).strip().lower()
    if not framework:
        return dict(config)

    root = {}
    framework_payload = {}

    for key, value in config.items():
        if key == framework and isinstance(value, dict):
            framework_payload.update(value)
        elif key in COMMON_PROJECT_KEYS:
            root[key] = value
        else:
            framework_payload[key] = value

    if framework_payload:
        root[framework] = framework_payload

    return root


def load_project_config(project_path: str) -> dict:
    config_file = Path(project_path) / ".mcp-config.json"
    if config_file.exists():
        return _normalize_project_config(json.loads(config_file.read_text()))
    return {}


def save_project_config(project_path: str, config: dict):
    config_file = Path(project_path) / ".mcp-config.json"
    config_file.write_text(json.dumps(_split_project_config(config), indent=2))
