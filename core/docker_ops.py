import subprocess


def _docker(command: str, cwd: str = None) -> str:
    try:
        result = subprocess.run(
            f"docker {command}",
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return (result.stdout + result.stderr).strip() or "(No output)"
    except Exception as e:
        return f"❌ Docker error: {e}"


def docker_ps(project_path: str = None) -> str:
    return _docker("ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}'")


def docker_compose_up(project_path: str, detach: bool = True) -> str:
    flag = "-d" if detach else ""
    return _docker(f"compose up {flag}", cwd=project_path)


def docker_compose_down(project_path: str) -> str:
    return _docker("compose down", cwd=project_path)


def docker_logs(container_name: str, n: int = 50) -> str:
    return _docker(f"logs --tail {n} {container_name}")


def docker_exec(container_name: str, command: str) -> str:
    return _docker(f"exec {container_name} {command}")


def docker_restart(container_name: str) -> str:
    return _docker(f"restart {container_name}")
