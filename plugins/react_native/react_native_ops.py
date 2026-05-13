from pathlib import Path

from plugins.shared import collect_files, run_command, run_package_script, summarize_paths


def react_native_test(project_path: str) -> str:
    return run_package_script(project_path, "test", timeout=240)


def react_native_android_build(project_path: str) -> str:
    android_dir = Path(project_path) / "android"
    if not android_dir.is_dir():
        return "ERROR: android/ directory not found."
    if not (android_dir / "gradlew").exists():
        return "ERROR: android/gradlew not found."
    return run_command("./gradlew assembleDebug", project_path, timeout=300, cwd="android")


def react_native_list_screens(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.tsx", "*.ts", "*.jsx", "*.js"),
        path_terms=("screens/", "screen/", "app/"),
        limit=80,
    )
    return summarize_paths("React Native screens:", files, "No React Native screen files found.")


def react_native_list_native_projects(project_path: str) -> str:
    root = Path(project_path)
    entries = []
    for name in ("android", "ios"):
        if (root / name).exists():
            entries.append(f"- {name}/")
    if not entries:
        return "No native Android or iOS folders found."
    return "React Native native folders:\n" + "\n".join(entries)


TOOLS = {
    "react_native_test": {"fn": react_native_test, "description": "Run React Native test script"},
    "react_native_android_build": {"fn": react_native_android_build, "description": "Build React Native Android app"},
    "react_native_list_screens": {"fn": react_native_list_screens, "description": "List React Native screen files"},
    "react_native_list_native_projects": {"fn": react_native_list_native_projects, "description": "List Android/iOS project folders"},
}
