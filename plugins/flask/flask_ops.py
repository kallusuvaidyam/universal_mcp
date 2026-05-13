import re
from pathlib import Path

from plugins.shared import collect_files, run_command, summarize_paths


ROUTE_RE = re.compile(r'@[\w\.]+\.route\(\s*["\']([^"\']+)["\']')


def flask_list_routes(project_path: str) -> str:
    root = Path(project_path)
    routes = []

    for path in sorted(root.rglob("*.py")):
        try:
            lines = path.read_text(errors="ignore").splitlines()
        except Exception:
            continue

        rel = path.relative_to(root).as_posix()
        for lineno, line in enumerate(lines, start=1):
            match = ROUTE_RE.search(line)
            if match:
                routes.append(f"- {match.group(1)} ({rel}:{lineno})")
                if len(routes) >= 80:
                    break
        if len(routes) >= 80:
            break

    if not routes:
        return "No Flask routes found."
    return "Flask routes:\n" + "\n".join(routes)


def flask_list_blueprints(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.py",),
        content_terms=("blueprint(",),
        limit=40,
    )
    return summarize_paths("Flask blueprint files:", files, "No Flask blueprint files found.")


def flask_run_tests(project_path: str) -> str:
    return run_command("pytest", project_path, timeout=300)


def flask_find_app_files(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.py",),
        content_terms=("flask(__name__)", "from flask import", "import flask"),
        limit=40,
    )
    return summarize_paths("Flask app files:", files, "No Flask app files found.")


TOOLS = {
    "flask_list_routes": {"fn": flask_list_routes, "description": "List Flask routes"},
    "flask_list_blueprints": {"fn": flask_list_blueprints, "description": "Find Flask blueprint files"},
    "flask_run_tests": {"fn": flask_run_tests, "description": "Run Flask test suite"},
    "flask_find_app_files": {"fn": flask_find_app_files, "description": "Find Flask app files"},
}
