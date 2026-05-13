from pathlib import Path

from plugins.shared import read_text


def _read_vscode_file(project_path: str, filename: str) -> str:
    path = Path(project_path) / ".vscode" / filename
    if not path.exists():
        return f"ERROR: .vscode/{filename} not found."
    return read_text(path)


def vscode_read_settings(project_path: str) -> str:
    return _read_vscode_file(project_path, "settings.json")


def vscode_read_launch_config(project_path: str) -> str:
    return _read_vscode_file(project_path, "launch.json")


def vscode_read_tasks(project_path: str) -> str:
    return _read_vscode_file(project_path, "tasks.json")


def vscode_read_extensions(project_path: str) -> str:
    return _read_vscode_file(project_path, "extensions.json")


TOOLS = {
    "vscode_read_settings": {"fn": vscode_read_settings, "description": "Read VS Code settings.json"},
    "vscode_read_launch_config": {"fn": vscode_read_launch_config, "description": "Read VS Code launch.json"},
    "vscode_read_tasks": {"fn": vscode_read_tasks, "description": "Read VS Code tasks.json"},
    "vscode_read_extensions": {"fn": vscode_read_extensions, "description": "Read VS Code extensions recommendations"},
}
