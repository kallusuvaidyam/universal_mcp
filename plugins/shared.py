"""Shared helpers for framework plugins."""
import json
import subprocess
from pathlib import Path


TEXT_LIMIT = 5000


def run_command(command: str, project_path: str, timeout: int = 120, cwd: str | None = None) -> str:
    root = Path(project_path)
    target = root / cwd if cwd else root

    if not target.exists():
        return f"ERROR: Working directory not found: {target}"

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=target,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except Exception as exc:
        return f"ERROR: {exc}"

    return (result.stdout + result.stderr).strip() or "(No output)"


def read_text(path: Path, limit: int = TEXT_LIMIT) -> str:
    if not path.exists():
        return f"ERROR: File not found: {path}"

    try:
        content = path.read_text(errors="ignore")
    except Exception as exc:
        return f"ERROR: {exc}"

    if len(content) > limit:
        return content[:limit] + "\n...[truncated]"
    return content


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def first_existing(project_path: str, candidates: list[str]) -> Path | None:
    root = Path(project_path)
    for candidate in candidates:
        path = root / candidate
        if path.exists():
            return path
    return None


def collect_files(
    project_path: str,
    patterns: tuple[str, ...] = ("*",),
    path_terms: tuple[str, ...] = (),
    name_terms: tuple[str, ...] = (),
    content_terms: tuple[str, ...] = (),
    limit: int = 40,
) -> list[str]:
    root = Path(project_path)
    path_terms = tuple(term.lower() for term in path_terms)
    name_terms = tuple(term.lower() for term in name_terms)
    content_terms = tuple(term.lower() for term in content_terms)
    seen = set()
    matches = []

    for pattern in patterns:
        for path in sorted(root.rglob(pattern)):
            if not path.is_file():
                continue

            rel = path.relative_to(root).as_posix()
            rel_lower = rel.lower()
            name_lower = path.name.lower()

            if path_terms and not any(term in rel_lower for term in path_terms):
                continue

            if name_terms and not any(term in name_lower for term in name_terms):
                continue

            if content_terms:
                try:
                    content = path.read_text(errors="ignore").lower()
                except Exception:
                    continue
                if not any(term in content for term in content_terms):
                    continue

            if rel in seen:
                continue

            seen.add(rel)
            matches.append(rel)
            if len(matches) >= limit:
                return matches

    return matches


def summarize_paths(title: str, paths: list[str], empty_message: str) -> str:
    if not paths:
        return empty_message
    return title + "\n" + "\n".join(f"- {path}" for path in paths)


def read_package_json(project_path: str) -> dict:
    package_json = Path(project_path) / "package.json"
    if not package_json.exists():
        return {}
    return read_json(package_json)


def detect_package_manager(project_path: str) -> str:
    root = Path(project_path)
    if (root / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (root / "yarn.lock").exists():
        return "yarn"
    if (root / "bun.lock").exists() or (root / "bun.lockb").exists():
        return "bun"
    return "npm"


def list_package_scripts(project_path: str) -> dict:
    package_json = read_package_json(project_path)
    scripts = package_json.get("scripts", {})
    return scripts if isinstance(scripts, dict) else {}


def list_package_scripts_text(project_path: str) -> str:
    scripts = list_package_scripts(project_path)
    if not scripts:
        return "No package.json scripts found."
    lines = [f"- {name}: {command}" for name, command in sorted(scripts.items())]
    return "Package scripts:\n" + "\n".join(lines)


def run_package_script(project_path: str, script: str, timeout: int = 180) -> str:
    scripts = list_package_scripts(project_path)
    if script not in scripts:
        available = ", ".join(sorted(scripts)) or "none"
        return f"ERROR: Script '{script}' not found. Available scripts: {available}"

    package_manager = detect_package_manager(project_path)
    if package_manager == "pnpm":
        command = f"pnpm {script}"
    elif package_manager == "yarn":
        command = f"yarn {script}"
    elif package_manager == "bun":
        command = f"bun run {script}"
    else:
        command = f"npm run {script}"

    return run_command(command, project_path, timeout=timeout)
