import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass
class _Session:
    session_id: str
    project_path: str
    last_pid: Optional[int] = None


class TerminalManager:
    """Internal multi-session terminal executor.

    Note: This is internal-only. MCP tools will NOT be exposed for
    terminal_session_* (as per requirements).
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._sessions: Dict[str, _Session] = {}

    def start_session(self, session_id: str, project_path: str) -> str:
        root = Path(project_path)
        if not root.exists() or not root.is_dir():
            return f"❌ Invalid project_path: {project_path}"

        with self._lock:
            self._sessions[session_id] = _Session(
                session_id=session_id,
                project_path=str(root.resolve()),
                last_pid=None,
            )
        return f"✅ Terminal session started: {session_id}"

    def run_in_session(self, session_id: str, command: str, timeout: int = 60) -> str:
        with self._lock:
            sess = self._sessions.get(session_id)

        if not sess:
            return f"❌ No such terminal session: {session_id}"

        # Basic safety (reuse idea from shell_executor, but scoped to this internal use)
        cmd_lower = (command or "").lower()
        blocked = [
            "rm -rf /", "mkfs", "dd if=", ":(){:|:&};:",
            "shutdown", "reboot", "halt", "poweroff",
        ]
        for b in blocked:
            if b in cmd_lower:
                return f"❌ Blocked command fragment: '{b}'"

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=sess.project_path,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            out = ""
            if result.stdout:
                out += result.stdout
            if result.stderr:
                out += result.stderr
            if result.returncode != 0:
                out += f"\n[Exit code: {result.returncode}]"
            return out.strip() or "(No output)"
        except subprocess.TimeoutExpired:
            return f"❌ Timeout: Command took more than {timeout} seconds."
        except Exception as e:
            return f"❌ Error: {e}"

    def stop_session(self, session_id: str) -> str:
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return f"✅ Terminal session stopped: {session_id}"
        return f"❌ No such terminal session: {session_id}"


# Singleton instance for simple import/use
terminal_manager = TerminalManager()


# Convenience module-level functions

def start_session(session_id: str, project_path: str) -> str:
    return terminal_manager.start_session(session_id, project_path)


def run_in_session(session_id: str, command: str, timeout: int = 60) -> str:
    return terminal_manager.run_in_session(session_id, command, timeout=timeout)


def stop_session(session_id: str) -> str:
    return terminal_manager.stop_session(session_id)

