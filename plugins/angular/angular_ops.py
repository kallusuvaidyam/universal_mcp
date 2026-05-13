from pathlib import Path

from plugins.shared import read_json, run_package_script


def angular_build(project_path: str) -> str:
    return run_package_script(project_path, "build", timeout=240)


def angular_test(project_path: str) -> str:
    return run_package_script(project_path, "test", timeout=240)


def angular_lint(project_path: str) -> str:
    return run_package_script(project_path, "lint", timeout=240)


def angular_list_projects(project_path: str) -> str:
    config_path = Path(project_path) / "angular.json"
    if not config_path.exists():
        return "ERROR: angular.json not found."

    projects = sorted(read_json(config_path).get("projects", {}).keys())
    if not projects:
        return "No Angular projects found in angular.json."

    return "Angular projects:\n" + "\n".join(f"- {name}" for name in projects)


TOOLS = {
    "angular_build": {"fn": angular_build, "description": "Build Angular project"},
    "angular_test": {"fn": angular_test, "description": "Run Angular test script"},
    "angular_lint": {"fn": angular_lint, "description": "Run Angular lint script"},
    "angular_list_projects": {"fn": angular_list_projects, "description": "List Angular workspace projects"},
}
