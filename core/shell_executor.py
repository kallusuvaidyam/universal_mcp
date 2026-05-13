import subprocess
import os
import shlex


# Commands that are too dangerous to allow
BLOCKED_COMMANDS = [
    "rm -rf /", "mkfs", "dd if=", ":(){:|:&};:", "shutdown", "reboot",
    "halt", "poweroff", "chmod 777 /", "chown root",
]


def shell_run(command: str, project_path: str, timeout: int = 60) -> str:
    """
    Run any shell command inside the project directory.
    Output is returned as string.
    """
    # Safety check
    cmd_lower = command.lower()
    for blocked in BLOCKED_COMMANDS:
        if blocked in cmd_lower:
            return f"❌ Blocked: '{blocked}' is not allowed for safety."

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += result.stderr
        if result.returncode != 0:
            output += f"\n[Exit code: {result.returncode}]"
        return output.strip() or "(No output)"
    except subprocess.TimeoutExpired:
        return f"❌ Timeout: Command took more than {timeout} seconds."
    except Exception as e:
        return f"❌ Error: {e}"
