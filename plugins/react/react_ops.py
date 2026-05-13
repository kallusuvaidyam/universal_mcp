from plugins.shared import collect_files, run_package_script, summarize_paths


def react_build(project_path: str) -> str:
    return run_package_script(project_path, "build", timeout=240)


def react_test(project_path: str) -> str:
    return run_package_script(project_path, "test", timeout=240)


def react_lint(project_path: str) -> str:
    return run_package_script(project_path, "lint", timeout=240)


def react_list_components(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.jsx", "*.tsx", "*.js", "*.ts"),
        path_terms=("components/", "component/"),
        limit=60,
    )
    return summarize_paths(
        "React component files:",
        files,
        "No React component files found under component directories.",
    )


TOOLS = {
    "react_build": {"fn": react_build, "description": "Build React project"},
    "react_test": {"fn": react_test, "description": "Run React test script"},
    "react_lint": {"fn": react_lint, "description": "Run React lint script"},
    "react_list_components": {"fn": react_list_components, "description": "List React component files"},
}
