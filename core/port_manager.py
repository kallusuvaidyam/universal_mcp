import subprocess


def port_check(port: int = None) -> str:
    """Check which ports are in use. If port given, check that specific port."""
    try:
        if port:
            result = subprocess.run(
                ["lsof", "-i", f":{port}"],
                capture_output=True, text=True, timeout=10
            )
            if result.stdout.strip():
                return f"Port {port} is IN USE:\n{result.stdout.strip()}"
            return f"Port {port} is FREE ✓"
        else:
            result = subprocess.run(
                ["ss", "-tlnp"],
                capture_output=True, text=True, timeout=10
            )
            return "Listening ports:\n" + result.stdout.strip()
    except FileNotFoundError:
        # Fallback with netstat
        try:
            cmd = f"netstat -tlnp 2>/dev/null | grep ':{port} '" if port else "netstat -tlnp 2>/dev/null"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            return result.stdout.strip() or "No output from netstat"
        except Exception as e:
            return f"❌ Error: {e}"
    except Exception as e:
        return f"❌ Error: {e}"


def port_kill(port: int) -> str:
    """Kill process running on a specific port."""
    try:
        result = subprocess.run(
            ["fuser", "-k", f"{port}/tcp"],
            capture_output=True, text=True, timeout=10
        )
        return f"✅ Killed process on port {port}"
    except Exception as e:
        return f"❌ Error: {e}"
