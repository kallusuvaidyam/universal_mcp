import subprocess


def _artisan(command: str, project_path: str) -> str:
    try:
        result = subprocess.run(
            f"php artisan {command}",
            shell=True, cwd=project_path,
            capture_output=True, text=True, timeout=60,
        )
        return (result.stdout + result.stderr).strip() or "(No output)"
    except Exception as e:
        return f"❌ Error: {e}"


def laravel_migrate(project_path: str) -> str:
    return _artisan("migrate", project_path)


def laravel_migrate_fresh(project_path: str) -> str:
    return _artisan("migrate:fresh --seed", project_path)


def laravel_tinker(project_path: str, code: str) -> str:
    return _artisan(f'tinker --execute="{code}"', project_path)


def laravel_route_list(project_path: str) -> str:
    return _artisan("route:list", project_path)


def laravel_cache_clear(project_path: str) -> str:
    return _artisan("cache:clear", project_path)


def laravel_queue_work(project_path: str) -> str:
    return _artisan("queue:work --once", project_path)


# Tool metadata for plugin loader
TOOLS = {
    "laravel_migrate": {"fn": laravel_migrate, "description": "Run Laravel migrations"},
    "laravel_migrate_fresh": {"fn": laravel_migrate_fresh, "description": "Fresh migrate + seed"},
    "laravel_tinker": {"fn": laravel_tinker, "description": "Run code in Laravel Tinker"},
    "laravel_route_list": {"fn": laravel_route_list, "description": "List all Laravel routes"},
    "laravel_cache_clear": {"fn": laravel_cache_clear, "description": "Clear Laravel cache"},
}
