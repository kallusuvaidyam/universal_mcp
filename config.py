import json
import time as _time
from pathlib import Path

_global_config_cache: dict = {}
_global_config_ts: float = 0.0
_CONFIG_TTL = 5.0

GLOBAL_CONFIG_DIR = Path.home() / ".universal-dev-mcp"
GLOBAL_CONFIG_FILE = GLOBAL_CONFIG_DIR / "config.json"
GLOBAL_MCP_CONFIG_FILE = GLOBAL_CONFIG_DIR / "mcp-config.json"  # plugin/framework config
STATE_FILE = GLOBAL_CONFIG_DIR / "state.json"  # runtime state (active project path, etc.)
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

print("_time.time()", _time.time(), "now - _global_config_ts < _CONFIG_TTL", _time.time() - _global_config_ts < _CONFIG_TTL)


def load_global_config() -> dict:
    """Global config (~/.universal-dev-mcp/config.json) ko cache ke saath load karta hai.

    _CONFIG_TTL seconds tak cache fresh maani jaati hai — us dauraan disk read skip hota hai.
    File na mile to {} return hoti hai. Hamesha ek copy return hoti hai (cache safe rahe).
    """
    global _global_config_cache, _global_config_ts
    now = _time.time()
    if _global_config_cache and now - _global_config_ts < _CONFIG_TTL:
        return dict(_global_config_cache)
    if GLOBAL_CONFIG_FILE.exists():
        _global_config_cache = json.loads(GLOBAL_CONFIG_FILE.read_text())
    else:
        _global_config_cache = {}
    _global_config_ts = now
    return dict(_global_config_cache)


def save_global_config(config: dict):
    global _global_config_cache, _global_config_ts
    GLOBAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    GLOBAL_CONFIG_FILE.write_text(json.dumps(config, indent=2))
    _global_config_cache = dict(config)
    _global_config_ts = _time.time()


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_state(state: dict):
    GLOBAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


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


def load_global_mcp_config() -> dict:
    """Load global plugin/framework config from ~/.universal-dev-mcp/mcp-config.json"""
    if GLOBAL_MCP_CONFIG_FILE.exists():
        return _normalize_project_config(json.loads(GLOBAL_MCP_CONFIG_FILE.read_text()))
    return {}


def load_project_config(project_path: str) -> dict:
    """Load config with merge: global mcp-config → project .mcp-config.json (project wins)."""
    global_cfg = load_global_mcp_config()

    project_file = Path(project_path) / ".mcp-config.json"
    if project_file.exists():
        project_cfg = _normalize_project_config(json.loads(project_file.read_text()))
        # Deep merge: project overrides global, but global fills missing keys
        merged = {**global_cfg, **project_cfg}
        # Special case: site_credentials merge (don't overwrite, extend)
        if "site_credentials" in global_cfg and "site_credentials" in project_cfg:
            merged["site_credentials"] = {
                **global_cfg["site_credentials"],
                **project_cfg["site_credentials"],
            }
        # Special case: benches merge (combine both lists, deduplicate by id)
        if "benches" in global_cfg or "benches" in project_cfg:
            g_benches = {b["id"]: b for b in global_cfg.get("benches", []) if isinstance(b, dict) and "id" in b}
            p_benches = {b["id"]: b for b in project_cfg.get("benches", []) if isinstance(b, dict) and "id" in b}
            g_benches.update(p_benches)  # project overrides global for same id
            merged["benches"] = list(g_benches.values())
        return merged

    return global_cfg


def save_project_config(project_path: str, config: dict):
    config_file = Path(project_path) / ".mcp-config.json"
    config_file.write_text(json.dumps(_split_project_config(config), indent=2))
