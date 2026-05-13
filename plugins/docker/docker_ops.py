from plugins.shared import collect_files, first_existing, run_command, summarize_paths


def _compose_file(project_path: str) -> str | None:
    path = first_existing(
        project_path,
        ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"],
    )
    if not path:
        return None
    return path.name


def docker_list_files(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*",),
        name_terms=("dockerfile", ".dockerignore", "compose"),
        limit=40,
    )
    return summarize_paths("Docker-related files:", files, "No Docker-related files found.")


def docker_compose_config(project_path: str) -> str:
    compose_file = _compose_file(project_path)
    if not compose_file:
        return "ERROR: docker-compose or compose YAML file not found."
    return run_command(f"docker compose -f {compose_file} config", project_path, timeout=240)


def docker_compose_ps(project_path: str) -> str:
    compose_file = _compose_file(project_path)
    if not compose_file:
        return "ERROR: docker-compose or compose YAML file not found."
    return run_command(f"docker compose -f {compose_file} ps", project_path, timeout=240)


def docker_compose_logs(project_path: str, service: str = "", lines: int = 100) -> str:
    compose_file = _compose_file(project_path)
    if not compose_file:
        return "ERROR: docker-compose or compose YAML file not found."
    suffix = f" {service}" if service else ""
    return run_command(f"docker compose -f {compose_file} logs --tail {lines}{suffix}", project_path, timeout=240)


TOOLS = {
    "docker_list_files": {"fn": docker_list_files, "description": "List Docker-related files"},
    "docker_compose_config": {"fn": docker_compose_config, "description": "Render Docker Compose config"},
    "docker_compose_ps": {"fn": docker_compose_ps, "description": "Show Docker Compose service status"},
    "docker_compose_logs": {"fn": docker_compose_logs, "description": "Show Docker Compose logs"},
}
