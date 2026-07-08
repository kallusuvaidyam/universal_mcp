import subprocess


def _git(command: str, project_path: str) -> str:
    try:
        result = subprocess.run(
            f"git {command}",
            shell=True,
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        out = (result.stdout + result.stderr).strip()
        return out or "(No output)"
    except Exception as e:
        return f"❌ Git error: {e}"


def git_status(project_path: str) -> str:
    return _git("status", project_path)


def git_log(project_path: str, n: int = 10) -> str:
    return _git(f"log --oneline -n {n}", project_path)


def git_diff(project_path: str, file_path: str = "") -> str:
    cmd = f"diff {file_path}" if file_path else "diff"
    return _git(cmd, project_path)


def git_commit(project_path: str, message: str, add_all: bool = True) -> str:
    try:
        if add_all:
            subprocess.run(["git", "add", "-A"], cwd=project_path, capture_output=True, text=True, timeout=30)
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=project_path, capture_output=True, text=True, timeout=30
        )
        return (result.stdout + result.stderr).strip() or "(No output)"
    except Exception as e:
        return f"❌ Git error: {e}"


def git_push(project_path: str, branch: str = "") -> str:
    cmd = f"push origin {branch}" if branch else "push"
    return _git(cmd, project_path)


def git_branch(project_path: str) -> str:
    return _git("branch -a", project_path)


def git_checkout(project_path: str, branch: str) -> str:
    import re
    if not re.match(r'^[a-zA-Z0-9/_.\-]+$', branch):
        return f"❌ Invalid branch name: '{branch}'"
    try:
        result = subprocess.run(
            ["git", "checkout", branch],
            cwd=project_path, capture_output=True, text=True, timeout=30
        )
        return (result.stdout + result.stderr).strip() or "(No output)"
    except Exception as e:
        return f"❌ Git error: {e}"


def git_add(project_path: str, paths: str) -> str:
    """Stage specific paths (space-separated) without shell interpolation."""
    path_list = [p for p in paths.split() if p]
    if not path_list:
        return "❌ No paths given."
    try:
        subprocess.run(["git", "add", *path_list], cwd=project_path,
                       capture_output=True, text=True, timeout=30)
        return _git("status --short", project_path)
    except Exception as e:
        return f"❌ Git error: {e}"


def git_stash(project_path: str, action: str = "push", message: str = "") -> str:
    """Stash operations: push / pop / list / drop."""
    if action not in ("push", "pop", "list", "drop"):
        return "❌ action must be one of: push, pop, list, drop"
    if action == "push" and message:
        return _git(f'stash push -m "{message}"', project_path)
    return _git(f"stash {action}", project_path)


def git_pull(project_path: str, branch: str = "", rebase: bool = False) -> str:
    cmd = "pull"
    if rebase:
        cmd += " --rebase"
    if branch:
        cmd += f" origin {branch}"
    return _git(cmd, project_path)


def git_branch_create(project_path: str, name: str) -> str:
    """Create and switch to a new branch."""
    import re
    if not re.match(r'^[a-zA-Z0-9/_.\-]+$', name):
        return f"❌ Invalid branch name: '{name}'"
    try:
        result = subprocess.run(
            ["git", "switch", "-c", name],
            cwd=project_path, capture_output=True, text=True, timeout=30
        )
        return (result.stdout + result.stderr).strip() or "(No output)"
    except Exception as e:
        return f"❌ Git error: {e}"


def git_restore(project_path: str, file_path: str, staged: bool = False) -> str:
    """Discard working-tree changes to a file, or unstage it (staged=True)."""
    if not file_path:
        return "❌ file_path required (no bulk restore)."
    args = ["git", "restore"]
    if staged:
        args.append("--staged")
    args.append(file_path)
    try:
        result = subprocess.run(args, cwd=project_path, capture_output=True, text=True, timeout=30)
        out = (result.stdout + result.stderr).strip()
        return out or f"✅ Restored {file_path}."
    except Exception as e:
        return f"❌ Git error: {e}"


def git_show_file(project_path: str, path: str, rev: str = "HEAD") -> str:
    """Show a file's contents at a given revision."""
    try:
        result = subprocess.run(
            ["git", "show", f"{rev}:{path}"],
            cwd=project_path, capture_output=True, text=True, timeout=30
        )
        return (result.stdout + result.stderr).strip() or "(No output)"
    except Exception as e:
        return f"❌ Git error: {e}"
