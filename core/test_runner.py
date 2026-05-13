import subprocess
from pathlib import Path


def _detect_test_tool(project_path: str) -> str:
    root = Path(project_path)
    if (root / "pytest.ini").exists() or (root / "pyproject.toml").exists():
        return "pytest"
    if (root / "requirements.txt").exists():
        try:
            content = (root / "requirements.txt").read_text()
            if "pytest" in content:
                return "pytest"
        except Exception:
            pass
    if (root / "package.json").exists():
        try:
            import json
            pkg = json.loads((root / "package.json").read_text())
            scripts = pkg.get("scripts", {})
            if "test" in scripts:
                return "npm test"
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            if "jest" in deps:
                return "npx jest"
            if "vitest" in deps:
                return "npx vitest"
        except Exception:
            pass
        return "npm test"
    if (root / "phpunit.xml").exists() or (root / "phpunit.xml.dist").exists():
        return "./vendor/bin/phpunit"
    if (root / "Gemfile").exists():
        return "bundle exec rspec"
    if (root / "Cargo.toml").exists():
        return "cargo test"
    if (root / "go.mod").exists():
        return "go test ./..."
    return None


def test_run(project_path: str, path: str = "") -> str:
    """Auto-detect test tool and run tests."""
    tool = _detect_test_tool(project_path)
    if not tool:
        return "❌ Could not detect test tool. Manually specify command using shell_run."

    cmd = f"{tool} {path}".strip()
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = (result.stdout + result.stderr).strip()
        status = "✅ Tests passed" if result.returncode == 0 else "❌ Tests failed"
        return f"{status} (using: {tool})\n\n{output}"
    except subprocess.TimeoutExpired:
        return "❌ Tests timed out after 120 seconds."
    except Exception as e:
        return f"❌ Error running tests: {e}"
