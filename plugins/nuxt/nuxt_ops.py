from plugins.shared import (
    collect_files,
    first_existing,
    read_text,
    run_package_script,
    summarize_paths,
)


def nuxt_build(project_path: str) -> str:
    return run_package_script(project_path, "build", timeout=300)


def nuxt_test(project_path: str) -> str:
    return run_package_script(project_path, "test", timeout=240)


def nuxt_show_config(project_path: str) -> str:
    config_path = first_existing(project_path, ["nuxt.config.ts", "nuxt.config.js", "nuxt.config.mjs"])
    if not config_path:
        return "ERROR: Nuxt config not found."
    return read_text(config_path)


def nuxt_list_routes(project_path: str) -> str:
    routes = collect_files(
        project_path,
        patterns=("*.vue", "*.js", "*.ts"),
        path_terms=("pages/", "app/pages/"),
        limit=80,
    )
    if not routes:
        return "No Nuxt page files found."
    return summarize_paths("Nuxt page routes:", routes, "No Nuxt page files found.")


def nuxt_list_server_api(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.ts", "*.js"),
        path_terms=("server/api/", "server/routes/"),
        limit=80,
    )
    return summarize_paths("Nuxt server API files:", files, "No Nuxt server API files found.")


TOOLS = {
    "nuxt_build": {"fn": nuxt_build, "description": "Build Nuxt project"},
    "nuxt_test": {"fn": nuxt_test, "description": "Run Nuxt test script"},
    "nuxt_show_config": {"fn": nuxt_show_config, "description": "Read Nuxt config file"},
    "nuxt_list_routes": {"fn": nuxt_list_routes, "description": "List Nuxt page route files"},
    "nuxt_list_server_api": {"fn": nuxt_list_server_api, "description": "List Nuxt server API files"},
}
