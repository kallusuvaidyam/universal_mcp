from pathlib import Path
from core.file_manager import _safe_path

# Keys that should never be exposed
SENSITIVE_KEYS = [
    "password", "secret", "private_key", "api_key", "token",
    "aws_secret", "database_url", "db_password",
]


def env_read(project_path: str, env_file: str = ".env", hide_secrets: bool = True) -> str:
    """Read .env file, optionally masking sensitive values."""
    target = _safe_path(project_path, env_file)
    if not target:
        return "❌ Access denied."
    if not target.exists():
        return f"❌ {env_file} not found in project."

    lines = target.read_text(errors="replace").splitlines()
    result = []

    for line in lines:
        if "=" in line and not line.startswith("#"):
            key, _, val = line.partition("=")
            key_lower = key.lower().strip()
            if hide_secrets and any(s in key_lower for s in SENSITIVE_KEYS):
                result.append(f"{key.strip()}=****")
            else:
                result.append(line)
        else:
            result.append(line)

    return "\n".join(result)


def env_get(project_path: str, key: str, env_file: str = ".env") -> str:
    """Get a specific env key value."""
    target = _safe_path(project_path, env_file)
    if not target or not target.exists():
        return f"❌ {env_file} not found."

    for line in target.read_text().splitlines():
        if line.startswith(f"{key}="):
            _, _, val = line.partition("=")
            return val.strip()

    return f"❌ Key '{key}' not found in {env_file}"
