"""Generic plugin — loaded when no specific framework is detected."""
import subprocess
from pathlib import Path


def generic_run_dev(project_path: str) -> str:
    """Try common dev server start commands."""
    root = Path(project_path)
    candidates = []

    if (root / "package.json").exists():
        import json
        try:
            pkg = json.loads((root / "package.json").read_text())
            scripts = pkg.get("scripts", {})
            if "dev" in scripts:
                candidates.append("npm run dev")
            elif "start" in scripts:
                candidates.append("npm start")
        except Exception:
            candidates.append("npm start")

    if (root / "Makefile").exists():
        candidates.append("make run")

    if not candidates:
        return "❌ Could not detect dev server command. Use shell_run manually."

    cmd = candidates[0]
    return f"To start dev server, run:\n  {cmd}\n\nOr use shell_run tool with your custom command."


def generic_readme(project_path: str) -> str:
    """Read README.md for project info."""
    for name in ["README.md", "README.txt", "README.rst", "readme.md"]:
        path = Path(project_path) / name
        if path.exists():
            content = path.read_text(errors="replace")
            if len(content) > 5000:
                content = content[:5000] + "\n...[truncated]"
            return content
    return "❌ No README found."


# Tool metadata for plugin loader
TOOLS = {
    "generic_run_dev": {"fn": generic_run_dev, "description": "Detect and suggest dev server command"},
    "generic_readme": {"fn": generic_readme, "description": "Read project README"},
}
