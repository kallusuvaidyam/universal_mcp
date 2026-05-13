import re
from pathlib import Path

from plugins.shared import collect_files, run_command, summarize_paths


ROUTE_RE = re.compile(r'@[\w\.]+\.(get|post|put|delete|patch|options|head)\(\s*["\']([^"\']+)["\']')


def fastapi_list_routes(project_path: str) -> str:
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
                method = match.group(1).upper()
                route = match.group(2)
                routes.append(f"- [{method}] {route} ({rel}:{lineno})")
                if len(routes) >= 80:
                    break
        if len(routes) >= 80:
            break

    if not routes:
        return "No FastAPI routes found."
    return "FastAPI routes:\n" + "\n".join(routes)


def fastapi_list_app_files(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.py",),
        content_terms=("fastapi(", "fastapi import", "from fastapi import"),
        limit=40,
    )
    return summarize_paths("FastAPI app files:", files, "No FastAPI app files found.")


def fastapi_run_tests(project_path: str) -> str:
    return run_command("pytest", project_path, timeout=300)


def fastapi_list_openapi_files(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.json", "*.yaml", "*.yml"),
        path_terms=("openapi", "schema"),
        limit=40,
    )
    return summarize_paths("OpenAPI/schema files:", files, "No OpenAPI or schema files found.")


TOOLS = {
    "fastapi_list_routes": {"fn": fastapi_list_routes, "description": "List FastAPI routes"},
    "fastapi_list_app_files": {"fn": fastapi_list_app_files, "description": "Find FastAPI app files"},
    "fastapi_run_tests": {"fn": fastapi_run_tests, "description": "Run FastAPI test suite"},
    "fastapi_list_openapi_files": {"fn": fastapi_list_openapi_files, "description": "List OpenAPI/schema files"},
}
