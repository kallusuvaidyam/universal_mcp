from plugins.shared import collect_files, first_existing, read_text, run_command, summarize_paths


def playwright_test(project_path: str, target: str = "") -> str:
    suffix = f" {target}" if target else ""
    return run_command(f"npx playwright test{suffix}", project_path, timeout=300)


def playwright_show_config(project_path: str) -> str:
    config_path = first_existing(
        project_path,
        [
            "playwright.config.ts",
            "playwright.config.js",
            "playwright.config.mjs",
            "playwright.config.cjs",
        ],
    )
    if not config_path:
        return "ERROR: Playwright config not found."
    return read_text(config_path)


def playwright_list_specs(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=(
            "*.spec.ts",
            "*.spec.tsx",
            "*.spec.js",
            "*.spec.jsx",
            "*.test.ts",
            "*.test.tsx",
            "*.test.js",
            "*.test.jsx",
        ),
        limit=80,
    )
    return summarize_paths("Playwright specs:", files, "No Playwright specs found.")


def playwright_list_artifacts(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.zip", "*.png", "*.webm", "*.json"),
        path_terms=("playwright-report/", "test-results/",),
        limit=80,
    )
    return summarize_paths("Playwright artifacts:", files, "No Playwright report artifacts found.")


TOOLS = {
    "playwright_test": {"fn": playwright_test, "description": "Run Playwright tests"},
    "playwright_show_config": {"fn": playwright_show_config, "description": "Read Playwright config file"},
    "playwright_list_specs": {"fn": playwright_list_specs, "description": "List Playwright spec files"},
    "playwright_list_artifacts": {"fn": playwright_list_artifacts, "description": "List Playwright report artifacts"},
}
