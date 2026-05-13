import os
from pathlib import Path


def _safe_path(project_path: str, rel_path: str) -> Path | None:
    """Ensure path stays within project directory (jail)."""
    base = Path(project_path).resolve()
    target = (base / rel_path).resolve()
    if not str(target).startswith(str(base)):
        return None
    return target


def file_read(project_path: str, rel_path: str) -> str:
    """Read any file inside the project directory."""
    target = _safe_path(project_path, rel_path)
    if not target:
        return "❌ Access denied: Path is outside project directory."
    if not target.exists():
        return f"❌ File not found: {rel_path}"
    if not target.is_file():
        return f"❌ Not a file: {rel_path}"
    try:
        content = target.read_text(errors="replace")
        # Limit output size
        if len(content) > 50000:
            content = content[:50000] + "\n\n... [truncated — file too large]"
        return content
    except Exception as e:
        return f"❌ Read error: {e}"


def file_write(project_path: str, rel_path: str, content: str) -> str:
    """Write/create any file inside the project directory."""
    target = _safe_path(project_path, rel_path)
    if not target:
        return "❌ Access denied: Path is outside project directory."
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        return f"✅ File written: {rel_path} ({len(content)} chars)"
    except Exception as e:
        return f"❌ Write error: {e}"


def file_search(project_path: str, pattern: str, file_pattern: str = "*") -> str:
    """Search for text pattern across project files."""
    import subprocess
    try:
        result = subprocess.run(
            ["grep", "-r", "--include", file_pattern, "-n", "-l", pattern, "."],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.stdout.strip():
            files = result.stdout.strip().split("\n")
            return f"Found '{pattern}' in {len(files)} file(s):\n" + "\n".join(files)
        return f"No matches found for '{pattern}'"
    except Exception as e:
        return f"❌ Search error: {e}"


def file_list(project_path: str, rel_path: str = ".") -> str:
    """List files/folders in a directory."""
    target = _safe_path(project_path, rel_path)
    if not target:
        return "❌ Access denied."
    if not target.is_dir():
        return f"❌ Not a directory: {rel_path}"
    try:
        items = sorted(target.iterdir(), key=lambda x: (x.is_file(), x.name))
        lines = []
        for item in items:
            if item.name.startswith("."):
                continue
            prefix = "📁 " if item.is_dir() else "📄 "
            lines.append(f"{prefix}{item.name}")
        return f"Contents of {rel_path}:\n" + "\n".join(lines)
    except Exception as e:
        return f"❌ List error: {e}"
