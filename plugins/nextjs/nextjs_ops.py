import subprocess


def _npm(command: str, project_path: str) -> str:
    try:
        result = subprocess.run(
            command, shell=True, cwd=project_path,
            capture_output=True, text=True, timeout=120,
        )
        return (result.stdout + result.stderr).strip() or "(No output)"
    except Exception as e:
        return f"❌ Error: {e}"


def nextjs_build(project_path: str) -> str:
    return _npm("npm run build", project_path)


def nextjs_lint(project_path: str) -> str:
    return _npm("npm run lint", project_path)


def nextjs_type_check(project_path: str) -> str:
    return _npm("npx tsc --noEmit", project_path)


def nextjs_list_routes(project_path: str) -> str:
    """List all Next.js pages/routes."""
    from pathlib import Path
    root = Path(project_path)
    pages_dirs = [root / "pages", root / "app", root / "src/pages", root / "src/app"]
    routes = []
    for pages_dir in pages_dirs:
        if pages_dir.exists():
            for pattern in ("*.js", "*.jsx", "*.ts", "*.tsx"):
                for f in pages_dir.rglob(pattern):
                    rel = str(f.relative_to(pages_dir))
                    route = "/" + rel.replace("index.js", "").replace("index.tsx", "").replace(".js", "").replace(".jsx", "").replace(".tsx", "").replace(".ts", "")
                    if not route.startswith("/_") and "node_modules" not in route:
                        routes.append(route)
    if routes:
        return "Routes:\n" + "\n".join(sorted(set(routes)))
    return "No routes found (check pages/ or app/ directory)"


# Tool metadata for plugin loader
TOOLS = {
    "nextjs_build": {"fn": nextjs_build, "description": "Build Next.js project"},
    "nextjs_lint": {"fn": nextjs_lint, "description": "Lint Next.js project"},
    "nextjs_type_check": {"fn": nextjs_type_check, "description": "TypeScript type check"},
    "nextjs_list_routes": {"fn": nextjs_list_routes, "description": "List all Next.js routes"},
}
