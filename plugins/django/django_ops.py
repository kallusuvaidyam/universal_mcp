import subprocess


def _manage(command: str, project_path: str) -> str:
    try:
        result = subprocess.run(
            f"python manage.py {command}",
            shell=True, cwd=project_path,
            capture_output=True, text=True, timeout=60,
        )
        return (result.stdout + result.stderr).strip() or "(No output)"
    except Exception as e:
        return f"❌ Error: {e}"


def django_migrate(project_path: str) -> str:
    return _manage("migrate", project_path)


def django_makemigrations(project_path: str, app: str = "") -> str:
    return _manage(f"makemigrations {app}", project_path)


def django_shell(project_path: str, code: str) -> str:
    return _manage(f'shell -c "{code}"', project_path)


def django_collectstatic(project_path: str) -> str:
    return _manage("collectstatic --noinput", project_path)


def django_createsuperuser(project_path: str) -> str:
    return _manage("createsuperuser", project_path)


def django_check(project_path: str) -> str:
    return _manage("check", project_path)


# Tool metadata for plugin loader
TOOLS = {
    "django_migrate": {"fn": django_migrate, "description": "Run Django migrations"},
    "django_makemigrations": {"fn": django_makemigrations, "description": "Create Django migrations"},
    "django_shell": {"fn": django_shell, "description": "Run code in Django shell"},
    "django_check": {"fn": django_check, "description": "Run Django system checks"},
    "django_collectstatic": {"fn": django_collectstatic, "description": "Collect static files"},
}
