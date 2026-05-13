from plugins.shared import list_package_scripts_text, run_package_script


def node_list_scripts(project_path: str) -> str:
    return list_package_scripts_text(project_path)


def node_run_script(project_path: str, script: str) -> str:
    return run_package_script(project_path, script, timeout=240)


def node_test(project_path: str) -> str:
    return run_package_script(project_path, "test", timeout=240)


def node_build(project_path: str) -> str:
    return run_package_script(project_path, "build", timeout=240)


TOOLS = {
    "node_list_scripts": {"fn": node_list_scripts, "description": "List package.json scripts"},
    "node_run_script": {"fn": node_run_script, "description": "Run a package.json script"},
    "node_test": {"fn": node_test, "description": "Run Node test script"},
    "node_build": {"fn": node_build, "description": "Run Node build script"},
}
