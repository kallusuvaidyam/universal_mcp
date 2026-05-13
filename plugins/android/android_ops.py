import re

from plugins.shared import collect_files, first_existing, read_text, run_command, summarize_paths


def _gradle_command(project_path: str, task: str) -> str:
    gradlew = first_existing(project_path, ["gradlew", "gradlew.bat"])
    if not gradlew:
        return "ERROR: gradlew wrapper not found."

    command = "./gradlew" if gradlew.name == "gradlew" else "gradlew.bat"
    return run_command(f"{command} {task}", project_path, timeout=300)


def android_gradle_tasks(project_path: str) -> str:
    return _gradle_command(project_path, "tasks --all")


def android_build_debug(project_path: str) -> str:
    return _gradle_command(project_path, "assembleDebug")


def android_list_modules(project_path: str) -> str:
    settings_file = first_existing(project_path, ["settings.gradle", "settings.gradle.kts"])
    if not settings_file:
        return "ERROR: settings.gradle or settings.gradle.kts not found."

    content = read_text(settings_file, limit=20000)
    modules = sorted({f":{name}" for name in re.findall(r'["\']:(.+?)["\']', content)})
    if not modules:
        return "No Gradle modules found in settings file."

    return "Android modules:\n" + "\n".join(f"- {name}" for name in modules)


def android_list_manifests(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("AndroidManifest.xml",),
        limit=60,
    )
    return summarize_paths("Android manifests:", files, "No AndroidManifest.xml files found.")


TOOLS = {
    "android_gradle_tasks": {"fn": android_gradle_tasks, "description": "List Android Gradle tasks"},
    "android_build_debug": {"fn": android_build_debug, "description": "Build Android debug APK"},
    "android_list_modules": {"fn": android_list_modules, "description": "List Android Gradle modules"},
    "android_list_manifests": {"fn": android_list_manifests, "description": "List Android manifest files"},
}
