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
    if add_all:
        add_result = _git("add -A", project_path)
    result = _git(f'commit -m "{message}"', project_path)
    return result


def git_push(project_path: str, branch: str = "") -> str:
    cmd = f"push origin {branch}" if branch else "push"
    return _git(cmd, project_path)


def git_branch(project_path: str) -> str:
    return _git("branch -a", project_path)


def git_checkout(project_path: str, branch: str) -> str:
    return _git(f"checkout {branch}", project_path)
