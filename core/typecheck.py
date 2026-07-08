import subprocess
from pathlib import Path


def typecheck(project_path: str) -> str:
    """Run a TypeScript no-emit typecheck (tsc --noEmit) in the project root."""
    root = Path(project_path)
    if not (root / "tsconfig.json").exists():
        return "❌ No tsconfig.json found — not a TypeScript project."

    pm = "npx"
    if (root / "pnpm-lock.yaml").exists():
        cmd = "pnpm exec tsc --noEmit"
    elif (root / "yarn.lock").exists():
        cmd = "yarn tsc --noEmit"
    else:
        cmd = "npx tsc --noEmit"

    try:
        result = subprocess.run(
            cmd, shell=True, cwd=project_path,
            capture_output=True, text=True, timeout=180,
        )
        out = (result.stdout + result.stderr).strip()
        if result.returncode == 0:
            return "✅ No type errors.\n\n" + out if out else "✅ No type errors."
        return f"❌ Type errors found:\n\n{out}"
    except subprocess.TimeoutExpired:
        return "❌ Typecheck timed out."
    except Exception as e:
        return f"❌ Error: {e}"
