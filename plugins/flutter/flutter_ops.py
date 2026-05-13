from pathlib import Path

from plugins.shared import collect_files, run_command, summarize_paths


def flutter_pub_get(project_path: str) -> str:
    return run_command("flutter pub get", project_path, timeout=240)


def flutter_test(project_path: str) -> str:
    return run_command("flutter test", project_path, timeout=300)


def flutter_analyze(project_path: str) -> str:
    return run_command("flutter analyze", project_path, timeout=300)


def flutter_build_apk(project_path: str) -> str:
    return run_command("flutter build apk", project_path, timeout=600)


def flutter_list_screens(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.dart",),
        path_terms=("lib/screens/", "lib/screen/", "lib/pages/", "lib/views/"),
        limit=80,
    )
    if files:
        return summarize_paths("Flutter screen files:", files, "No Flutter screen files found.")

    root = Path(project_path)
    if not (root / "lib").is_dir():
        return "No lib/ directory found."

    fallback = collect_files(
        project_path,
        patterns=("*.dart",),
        path_terms=("lib/",),
        name_terms=("screen", "page", "view"),
        limit=80,
    )
    return summarize_paths("Flutter screen-like files:", fallback, "No Flutter screen files found.")


TOOLS = {
    "flutter_pub_get": {"fn": flutter_pub_get, "description": "Run flutter pub get"},
    "flutter_test": {"fn": flutter_test, "description": "Run Flutter tests"},
    "flutter_analyze": {"fn": flutter_analyze, "description": "Run flutter analyze"},
    "flutter_build_apk": {"fn": flutter_build_apk, "description": "Build Flutter Android APK"},
    "flutter_list_screens": {"fn": flutter_list_screens, "description": "List Flutter screen files"},
}
