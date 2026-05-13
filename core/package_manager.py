import subprocess
from pathlib import Path


def _detect_pm(project_path: str) -> str:
    root = Path(project_path)
    if (root / "package.json").exists():
        if (root / "yarn.lock").exists():
            return "yarn"
        if (root / "pnpm-lock.yaml").exists():
            return "pnpm"
        return "npm"
    if (root / "requirements.txt").exists() or (root / "pyproject.toml").exists():
        return "pip"
    if (root / "composer.json").exists():
        return "composer"
    if (root / "Gemfile").exists():
        return "bundle"
    if (root / "Cargo.toml").exists():
        return "cargo"
    if (root / "go.mod").exists():
        return "go"
    return None


def package_install(project_path: str, package: str = "") -> str:
    """Auto-detect package manager and install package (or all deps if no package given)."""
    pm = _detect_pm(project_path)
    if not pm:
        return "❌ Could not detect package manager."

    if package:
        cmd_map = {
            "npm": f"npm install {package}",
            "yarn": f"yarn add {package}",
            "pnpm": f"pnpm add {package}",
            "pip": f"pip install {package}",
            "composer": f"composer require {package}",
            "bundle": f"bundle add {package}",
            "cargo": f"cargo add {package}",
        }
        cmd = cmd_map.get(pm, f"{pm} install {package}")
    else:
        cmd_map = {
            "npm": "npm install",
            "yarn": "yarn install",
            "pnpm": "pnpm install",
            "pip": "pip install -r requirements.txt",
            "composer": "composer install",
            "bundle": "bundle install",
            "cargo": "cargo build",
        }
        cmd = cmd_map.get(pm, f"{pm} install")

    try:
        result = subprocess.run(
            cmd, shell=True, cwd=project_path,
            capture_output=True, text=True, timeout=120,
        )
        output = (result.stdout + result.stderr).strip()
        status = "✅" if result.returncode == 0 else "❌"
        return f"{status} [{pm}] {cmd}\n\n{output}"
    except subprocess.TimeoutExpired:
        return "❌ Install timed out."
    except Exception as e:
        return f"❌ Error: {e}"


def package_list(project_path: str) -> str:
    """List installed packages."""
    pm = _detect_pm(project_path)
    if not pm:
        return "❌ Could not detect package manager."

    cmd_map = {
        "npm": "npm list --depth=0",
        "pip": "pip list",
        "composer": "composer show",
        "yarn": "yarn list --depth=0",
    }
    cmd = cmd_map.get(pm, f"{pm} list")
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=project_path,
            capture_output=True, text=True, timeout=30,
        )
        return f"[{pm} packages]\n\n" + (result.stdout + result.stderr).strip()
    except Exception as e:
        return f"❌ Error: {e}"
