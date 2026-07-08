import os
from pathlib import Path


def _safe_path(project_path: str, rel_path: str) -> Path | None:
    """Ensure path stays within project directory (jail)."""
    base = Path(project_path).resolve()
    target = (base / rel_path).resolve()
    if not str(target).startswith(str(base) + os.sep) and str(target) != str(base):
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


def file_edit(project_path: str, rel_path: str, old_string: str, new_string: str) -> str:
    """Replace an exact unique substring in a file (no full rewrite)."""
    target = _safe_path(project_path, rel_path)
    if not target:
        return "❌ Access denied: Path is outside project directory."
    if not target.is_file():
        return f"❌ Not a file: {rel_path}"
    try:
        content = target.read_text(errors="replace")
        count = content.count(old_string)
        if count == 0:
            return "❌ old_string not found. Match must be exact (whitespace included)."
        if count > 1:
            return f"❌ old_string matches {count} times — make it unique so only one place is edited."
        target.write_text(content.replace(old_string, new_string, 1))
        return f"✅ Edited {rel_path} (1 replacement)."
    except Exception as e:
        return f"❌ Edit error: {e}"


def file_grep(project_path: str, pattern: str, file_pattern: str = "*", context: int = 0) -> str:
    """Search for text and return file:line:content matches (not just filenames)."""
    import subprocess
    cmd = ["grep", "-rn", "--include", file_pattern,
           "--exclude-dir", "node_modules", "--exclude-dir", ".git",
           "--exclude-dir", "__pycache__"]
    if context and context > 0:
        cmd += ["-C", str(context)]
    cmd += [pattern, "."]
    try:
        result = subprocess.run(cmd, cwd=project_path, capture_output=True, text=True, timeout=30)
        out = result.stdout.strip()
        if not out:
            return f"No matches found for '{pattern}'"
        lines = out.split("\n")
        if len(lines) > 200:
            lines = lines[:200]
            lines.append(f"... [truncated — {len(out.splitlines())} total matches]")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Search error: {e}"


def file_read_lines(project_path: str, rel_path: str, offset: int = 1, limit: int = 200) -> str:
    """Read a file with line numbers, starting at line `offset`, up to `limit` lines."""
    target = _safe_path(project_path, rel_path)
    if not target:
        return "❌ Access denied: Path is outside project directory."
    if not target.is_file():
        return f"❌ Not a file: {rel_path}"
    try:
        all_lines = target.read_text(errors="replace").splitlines()
        start = max(offset, 1) - 1
        chunk = all_lines[start:start + limit]
        numbered = [f"{start + i + 1}\t{line}" for i, line in enumerate(chunk)]
        header = f"[{rel_path}] lines {start + 1}-{start + len(chunk)} of {len(all_lines)}"
        return header + "\n" + "\n".join(numbered)
    except Exception as e:
        return f"❌ Read error: {e}"


def file_append(project_path: str, rel_path: str, content: str) -> str:
    """Append text to a file (creates it if missing)."""
    target = _safe_path(project_path, rel_path)
    if not target:
        return "❌ Access denied: Path is outside project directory."
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "a") as f:
            f.write(content)
        return f"✅ Appended {len(content)} chars to {rel_path}."
    except Exception as e:
        return f"❌ Append error: {e}"


def file_delete(project_path: str, rel_path: str, recursive: bool = False) -> str:
    """Delete a file, or a directory only when recursive=True."""
    target = _safe_path(project_path, rel_path)
    if not target:
        return "❌ Access denied: Path is outside project directory."
    if not target.exists():
        return f"❌ Not found: {rel_path}"
    try:
        if target.is_dir():
            if not recursive:
                return f"❌ '{rel_path}' is a directory. Pass recursive=True to delete it."
            import shutil
            shutil.rmtree(target)
            return f"✅ Deleted directory {rel_path}."
        target.unlink()
        return f"✅ Deleted file {rel_path}."
    except Exception as e:
        return f"❌ Delete error: {e}"


def file_move(project_path: str, src: str, dst: str, overwrite: bool = False) -> str:
    """Move/rename a file or directory within the project."""
    src_path = _safe_path(project_path, src)
    dst_path = _safe_path(project_path, dst)
    if not src_path or not dst_path:
        return "❌ Access denied: Path is outside project directory."
    if not src_path.exists():
        return f"❌ Source not found: {src}"
    if dst_path.exists() and not overwrite:
        return f"❌ Destination exists: {dst}. Pass overwrite=True to replace."
    try:
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.move(str(src_path), str(dst_path))
        return f"✅ Moved {src} → {dst}."
    except Exception as e:
        return f"❌ Move error: {e}"


def file_mkdir(project_path: str, rel_path: str) -> str:
    """Create a directory (including parents) inside the project."""
    target = _safe_path(project_path, rel_path)
    if not target:
        return "❌ Access denied: Path is outside project directory."
    try:
        target.mkdir(parents=True, exist_ok=True)
        return f"✅ Directory ready: {rel_path}."
    except Exception as e:
        return f"❌ Mkdir error: {e}"


_TREE_SKIP = {"node_modules", ".git", "__pycache__", ".venv", "venv", "dist", "build", ".next"}


def file_tree(project_path: str, rel_path: str = ".", max_depth: int = 3) -> str:
    """Recursive directory tree up to max_depth, skipping heavy dirs."""
    base = _safe_path(project_path, rel_path)
    if not base:
        return "❌ Access denied: Path is outside project directory."
    if not base.is_dir():
        return f"❌ Not a directory: {rel_path}"

    lines = []
    count = [0]
    cap = 500

    def walk(directory, prefix, depth):
        if depth > max_depth or count[0] >= cap:
            return
        try:
            entries = sorted(directory.iterdir(), key=lambda x: (x.is_file(), x.name))
        except Exception:
            return
        for item in entries:
            if item.name.startswith(".") or item.name in _TREE_SKIP:
                continue
            if count[0] >= cap:
                lines.append(f"{prefix}... [truncated]")
                return
            count[0] += 1
            marker = "📁 " if item.is_dir() else "📄 "
            lines.append(f"{prefix}{marker}{item.name}")
            if item.is_dir():
                walk(item, prefix + "  ", depth + 1)

    walk(base, "", 1)
    return f"Tree of {rel_path} (depth {max_depth}):\n" + "\n".join(lines)
