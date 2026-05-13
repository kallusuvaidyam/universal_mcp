"""
Desktop control using pyautogui + xdotool.
Works on Linux with X11 display.
"""
import subprocess
import time


def desktop_screenshot() -> str:
    try:
        import pyautogui
        path = "/tmp/mcp_desktop.png"
        screenshot = pyautogui.screenshot()
        screenshot.save(path)
        return f"✅ Desktop screenshot saved: {path}"
    except Exception as e:
        return f"❌ Screenshot error: {e}"


def desktop_click(x: int, y: int) -> str:
    try:
        import pyautogui
        pyautogui.click(x, y)
        return f"✅ Clicked at ({x}, {y})"
    except Exception as e:
        return f"❌ Click error: {e}"


def desktop_type(text: str) -> str:
    try:
        import pyautogui
        pyautogui.write(text, interval=0.02)
        return f"✅ Typed: {text[:50]}..."
    except Exception as e:
        return f"❌ Type error: {e}"


def desktop_key(keys: str) -> str:
    try:
        import pyautogui
        pyautogui.hotkey(*keys.split("+"))
        return f"✅ Key pressed: {keys}"
    except Exception as e:
        return f"❌ Key error: {e}"


def desktop_open_app(app: str) -> str:
    try:
        subprocess.Popen(app, shell=True)
        time.sleep(1)
        return f"✅ Opened: {app}"
    except Exception as e:
        return f"❌ Error opening app: {e}"


def desktop_get_windows() -> str:
    try:
        result = subprocess.run(
            ["wmctrl", "-l"],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip() or "No windows found"
    except Exception as e:
        return f"❌ Error: {e}"
