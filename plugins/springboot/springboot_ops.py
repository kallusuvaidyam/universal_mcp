from pathlib import Path

from plugins.shared import collect_files, first_existing, run_command, summarize_paths


def _spring_command(project_path: str, gradle_task: str, maven_task: str) -> str:
    root = Path(project_path)

    if (root / "gradlew").exists():
        return run_command(f"./gradlew {gradle_task}", project_path, timeout=300)
    if (root / "mvnw").exists():
        return run_command(f"./mvnw {maven_task}", project_path, timeout=300)
    if first_existing(project_path, ["build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts"]):
        return run_command(f"gradle {gradle_task}", project_path, timeout=300)
    if (root / "pom.xml").exists():
        return run_command(f"mvn {maven_task}", project_path, timeout=300)

    return "ERROR: No Maven or Gradle build file found."


def springboot_build(project_path: str) -> str:
    return _spring_command(project_path, "build", "package -DskipTests")


def springboot_test(project_path: str) -> str:
    return _spring_command(project_path, "test", "test")


def springboot_list_endpoints(project_path: str) -> str:
    root = Path(project_path)
    files = sorted(list(root.rglob("*.java")) + list(root.rglob("*.kt")))
    matches = []

    for path in files:
        try:
            lines = path.read_text(errors="ignore").splitlines()
        except Exception:
            continue

        rel = path.relative_to(root).as_posix()
        for lineno, line in enumerate(lines, start=1):
            stripped = line.strip()
            if any(tag in stripped for tag in ("@GetMapping", "@PostMapping", "@PutMapping", "@DeleteMapping", "@PatchMapping", "@RequestMapping")):
                matches.append(f"- {rel}:{lineno} {stripped}")
                if len(matches) >= 80:
                    break
        if len(matches) >= 80:
            break

    if not matches:
        return "No Spring Boot mapping annotations found."
    return "Spring Boot endpoint annotations:\n" + "\n".join(matches)


def springboot_list_config(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("application.properties", "application.yml", "application.yaml"),
        limit=20,
    )
    return summarize_paths("Spring Boot config files:", files, "No Spring Boot application config files found.")


TOOLS = {
    "springboot_build": {"fn": springboot_build, "description": "Build Spring Boot project"},
    "springboot_test": {"fn": springboot_test, "description": "Run Spring Boot tests"},
    "springboot_list_endpoints": {"fn": springboot_list_endpoints, "description": "List Spring Boot request mappings"},
    "springboot_list_config": {"fn": springboot_list_config, "description": "List Spring Boot config files"},
}
