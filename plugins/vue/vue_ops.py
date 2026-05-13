from plugins.shared import collect_files, run_package_script, summarize_paths


def vue_build(project_path: str) -> str:
    return run_package_script(project_path, "build", timeout=240)


def vue_test(project_path: str) -> str:
    return run_package_script(project_path, "test", timeout=240)


def vue_lint(project_path: str) -> str:
    return run_package_script(project_path, "lint", timeout=240)


def vue_list_views(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.vue",),
        path_terms=("views/", "pages/", "components/"),
        limit=60,
    )
    return summarize_paths(
        "Vue view/component files:",
        files,
        "No Vue view files found under views/, pages/, or components/.",
    )


TOOLS = {
    "vue_build": {"fn": vue_build, "description": "Build Vue project"},
    "vue_test": {"fn": vue_test, "description": "Run Vue test script"},
    "vue_lint": {"fn": vue_lint, "description": "Run Vue lint script"},
    "vue_list_views": {"fn": vue_list_views, "description": "List Vue view files"},
}
