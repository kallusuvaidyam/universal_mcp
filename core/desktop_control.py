"""
Desktop automation for Ubuntu GNOME/Wayland via XTEST + XWayland.
Ported from frappe-mcp — full implementation replacing basic pyautogui stub.
"""

import base64
import glob
import io
import os
import subprocess
import time
from typing import Optional

try:
    from PIL import Image as PILImage, ImageDraw
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


def _img(data: bytes, fmt: str = "jpeg") -> dict:
    return {"_image": True, "data": base64.b64encode(data).decode(), "format": fmt}


def _png_to_jpeg(png_bytes: bytes) -> bytes:
    if not _PIL_AVAILABLE:
        return png_bytes
    try:
        buf = io.BytesIO(png_bytes)
        img = PILImage.open(buf).convert("RGB")
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=70)
        return out.getvalue()
    except Exception:
        return png_bytes


def _setup_xauth() -> None:
    current = os.environ.get("XAUTHORITY", "")
    if current and os.path.exists(current):
        return
    uid = os.getuid()
    matches = glob.glob(f"/run/user/{uid}/.mutter-Xwaylandauth.*")
    if matches:
        os.environ["XAUTHORITY"] = matches[0]
        return
    home_auth = os.path.expanduser("~/.Xauthority")
    if os.path.exists(home_auth):
        os.environ["XAUTHORITY"] = home_auth


def _get_display_env() -> str:
    _setup_xauth()
    for candidate in [":0", os.environ.get("DISPLAY", ""), ":1"]:
        if not candidate:
            continue
        try:
            result = subprocess.run(
                ["xdpyinfo", "-display", candidate],
                capture_output=True, timeout=2,
            )
            if result.returncode == 0:
                return candidate
        except Exception:
            pass
    return ":0"


def _capture_active_window():
    """Capture focused X11 window via python-xlib. Returns (image_dict, info) or None."""
    if not _PIL_AVAILABLE:
        return None
    try:
        import Xlib as _xlib_mod
        try:
            _xlib_mod.threaded_init()
        except Exception:
            pass

        from Xlib import display as XDisplay, X

        display_name = _get_display_env()
        os.environ["DISPLAY"] = display_name
        d = XDisplay.Display(display_name)
        root = d.screen().root

        try:
            subprocess.run(["xset", f"-display", display_name, "s", "reset"],
                           capture_output=True, timeout=2)
        except Exception:
            pass

        prop = root.get_full_property(d.intern_atom("_NET_ACTIVE_WINDOW"), X.AnyPropertyType)
        win_id = prop.value[0] if (prop and prop.value) else 0

        if not win_id:
            cl = root.get_full_property(d.intern_atom("_NET_CLIENT_LIST"), X.AnyPropertyType)
            if cl and cl.value:
                win_id = cl.value[0]

        if not win_id:
            return None

        win = d.create_resource_object("window", win_id)

        name_prop = win.get_full_property(d.intern_atom("_NET_WM_NAME"), 0)
        if name_prop:
            name = name_prop.value if isinstance(name_prop.value, str) else name_prop.value.decode("utf-8", errors="replace")
        else:
            name = "unknown"

        trans = win.translate_coords(root, 0, 0)
        geom = win.get_geometry()
        W, H = geom.width, geom.height
        sx, sy = trans.x, trans.y

        raw = win.get_image(0, 0, W, H, X.ZPixmap, 0xFFFFFFFF)
        img = PILImage.frombytes("RGBX", (W, H), raw.data, "raw", "BGRX")

        sample = [img.getpixel((x, y)) for x in range(0, W, 100) for y in range(0, H, 100)]
        non_black = sum(1 for p in sample if p[0] > 15 or p[1] > 15 or p[2] > 15)
        if non_black == 0:
            return None

        draw = ImageDraw.Draw(img)
        bar_text = f"Window pos: x={sx}, y={sy}  |  Size: {W}x{H}  |  To click at image (ix,iy): desktop_click({sx}+ix, {sy}+iy)"
        draw.rectangle([0, H - 18, W, H], fill=(0, 0, 0))
        draw.text((4, H - 16), bar_text, fill=(255, 255, 0))

        out = io.BytesIO()
        img.save(out, "JPEG", quality=70)
        info = {"title": name, "screen_x": sx, "screen_y": sy, "width": W, "height": H}
        return _img(out.getvalue()), info
    except Exception:
        return None


def _build_desktop_env() -> dict:
    uid = os.getuid()
    xdg_runtime = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{uid}")
    passthrough = [
        "HOME", "USER", "LOGNAME", "SHELL",
        "LANG", "LANGUAGE", "LC_ALL", "LC_MESSAGES",
        "XDG_SESSION_TYPE", "GTK_IM_MODULE", "QT_IM_MODULE", "XMODIFIERS",
        "GNOME_DESKTOP_SESSION_ID", "DESKTOP_SESSION", "GDMSESSION",
        "GPG_AGENT_INFO", "SSH_AUTH_SOCK",
    ]
    env = {k: os.environ[k] for k in passthrough if k in os.environ}
    env.update({
        "DISPLAY": os.environ.get("DISPLAY", ":0"),
        "WAYLAND_DISPLAY": os.environ.get("WAYLAND_DISPLAY", "wayland-0"),
        "XDG_RUNTIME_DIR": xdg_runtime,
        "DBUS_SESSION_BUS_ADDRESS": os.environ.get(
            "DBUS_SESSION_BUS_ADDRESS", f"unix:path={xdg_runtime}/bus"
        ),
        "PATH": "/snap/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        "XDG_DATA_DIRS": "/usr/share/ubuntu:/usr/local/share:/usr/share:/var/lib/snapd/desktop",
        "XDG_CONFIG_DIRS": "/etc/xdg",
    })
    matches = glob.glob(f"{xdg_runtime}/.mutter-Xwaylandauth.*")
    if matches:
        env["XAUTHORITY"] = matches[0]
    return env


_KEY_MAP = {
    "enter": "Return", "return": "Return",
    "escape": "Escape", "esc": "Escape",
    "tab": "Tab", "space": "space",
    "backspace": "BackSpace", "delete": "Delete",
    "up": "Up", "down": "Down", "left": "Left", "right": "Right",
    "home": "Home", "end": "End", "pageup": "Page_Up", "pagedown": "Page_Down",
    "f1": "F1", "f2": "F2", "f3": "F3", "f4": "F4", "f5": "F5",
    "f6": "F6", "f7": "F7", "f8": "F8", "f9": "F9", "f10": "F10",
    "f11": "F11", "f12": "F12",
    "ctrl": "Control_L", "shift": "Shift_L", "alt": "Alt_L",
    "super": "super", "win": "super",
}

_BTN_MAP = {"left": 1, "middle": 2, "right": 3}


def _xtest_display():
    _setup_xauth()
    import Xlib as _xl
    try:
        _xl.threaded_init()
    except Exception:
        pass
    from Xlib import display as XDisplay
    return XDisplay.Display(":0")


def _xtest_press_key(d, keyname: str, press: bool):
    from Xlib.ext import xtest
    from Xlib import XK, X
    name = _KEY_MAP.get(keyname.lower(), keyname)
    keysym = XK.string_to_keysym(name)
    if keysym == 0:
        keysym = XK.string_to_keysym(keyname)
    keycode = d.keysym_to_keycode(keysym)
    if keycode == 0:
        raise ValueError(f"Unknown key: '{keyname}'")
    event = X.KeyPress if press else X.KeyRelease
    xtest.fake_input(d, event, keycode)
    d.sync()


def desktop_screenshot() -> dict:
    """
    Screenshot of the currently focused desktop window.
    Works on GNOME Wayland via XWayland.
    Bottom bar shows window screen position — use for click coordinate calculation.
    Example: bar says 'x=0, y=27', click at image point (200,150) → desktop_click(200, 177).
    """
    result = _capture_active_window()
    if result:
        img, _ = result
        return img

    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        ss = pyautogui.screenshot()
        buf = io.BytesIO()
        ss.save(buf, format="JPEG", quality=70)
        return _img(buf.getvalue())
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["scrot", "/tmp/_mcp_desktop.png", "--overwrite"],
            capture_output=True, timeout=5,
        )
        if result.returncode == 0:
            with open("/tmp/_mcp_desktop.png", "rb") as f:
                raw = f.read()
            jpeg = _png_to_jpeg(raw)
            return _img(jpeg)
    except Exception:
        pass

    return {"success": False, "error": "Screenshot failed. Install python-xlib: pip install python-xlib"}


def desktop_open_app(command: str, args: str = "", screenshot: bool = True) -> dict:
    """
    Open any desktop application or URL. Works on Wayland and X11.
    command: app name — 'firefox', 'nautilus', 'gedit', 'code'
    args: optional arguments — 'https://youtube.com', '/path/to/file'
    screenshot=True: waits 3s and returns window screenshot.
    """
    try:
        parts = [command] + (args.split() if args else [])
        env = _build_desktop_env()

        app_name = os.path.basename(command)
        raised = False
        for tool, try_args in [
            ("wmctrl", ["-a", app_name]),
            ("xdotool", ["search", "--class", app_name, "windowactivate"]),
        ]:
            try:
                r = subprocess.run([tool] + try_args, capture_output=True, timeout=2, env=env)
                if r.returncode == 0:
                    raised = True
                    break
            except Exception:
                pass

        if not raised:
            subprocess.Popen(parts, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if not screenshot:
            return {"success": True, "command": " ".join(parts), "action": "raised" if raised else "launched"}

        time.sleep(3)
        result = _capture_active_window()
        if result:
            img, _ = result
            return img

        return {"success": True, "command": " ".join(parts), "note": "App launched but screenshot unavailable. Try desktop_screenshot() manually."}
    except FileNotFoundError:
        return {"success": False, "error": f"'{command}' not found. Check the app name or install it."}
    except Exception as e:
        return {"success": False, "error": str(e)}


def desktop_click(x: int, y: int, button: str = "left") -> dict:
    """
    Click at exact screen coordinates. Works on Wayland/XWayland via XTEST.
    Use after desktop_screenshot() — read the bottom bar for screen offset.
    button: 'left' (default), 'right', 'middle'
    Returns a screenshot after clicking.
    """
    try:
        from Xlib.ext import xtest
        from Xlib import X
        d = _xtest_display()
        btn = _BTN_MAP.get(button, 1)
        d.screen().root.warp_pointer(x, y)
        d.sync()
        time.sleep(0.05)
        xtest.fake_input(d, X.ButtonPress, btn)
        d.sync()
        time.sleep(0.05)
        xtest.fake_input(d, X.ButtonRelease, btn)
        d.sync()
        time.sleep(0.4)

        result = _capture_active_window()
        if result:
            img, _ = result
            return img
        return {"success": True, "clicked": {"x": x, "y": y, "button": button},
                "note": "Click done but screenshot unavailable."}
    except Exception as e:
        return {"success": False, "error": str(e)}


def desktop_type(text: str, interval: float = 0.03) -> dict:
    """
    Type text at the currently focused window. Works on Wayland via XTEST.
    For Unicode text: uses clipboard paste (xclip) automatically.
    Click the target field first with desktop_click(), then call this.
    """
    try:
        from Xlib.ext import xtest
        from Xlib import X, XK
        d = _xtest_display()

        has_non_ascii = any(ord(c) > 127 for c in text)
        if has_non_ascii:
            try:
                proc = subprocess.Popen(
                    ["xclip", "-selection", "clipboard"],
                    stdin=subprocess.PIPE,
                    env={**os.environ, "DISPLAY": ":0"},
                )
                proc.communicate(input=text.encode("utf-8"))
                _xtest_press_key(d, "ctrl", True)
                _xtest_press_key(d, "v", True)
                time.sleep(0.05)
                _xtest_press_key(d, "v", False)
                _xtest_press_key(d, "ctrl", False)
                d.sync()
                return {"success": True, "typed": text[:200], "method": "clipboard"}
            except FileNotFoundError:
                pass

        for ch in text:
            keysym = XK.string_to_keysym(ch) or ord(ch)
            keycode = d.keysym_to_keycode(keysym)
            if keycode == 0:
                continue
            xtest.fake_input(d, X.KeyPress, keycode)
            d.sync()
            time.sleep(interval)
            xtest.fake_input(d, X.KeyRelease, keycode)
            d.sync()
            time.sleep(interval)
        return {"success": True, "typed": text[:200], "method": "xtest"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def desktop_key(keys: str) -> dict:
    """
    Press a key or keyboard shortcut. Works on Wayland/XWayland via XTEST.
    Single keys: 'enter', 'escape', 'tab', 'space', 'backspace', 'f5'
    Combos: 'ctrl+c', 'ctrl+v', 'alt+tab', 'ctrl+shift+i', 'ctrl+l'
    """
    try:
        d = _xtest_display()
        key_list = [k.strip() for k in keys.split("+")]
        for k in key_list:
            _xtest_press_key(d, k, True)
            time.sleep(0.03)
        time.sleep(0.05)
        for k in reversed(key_list):
            _xtest_press_key(d, k, False)
            time.sleep(0.03)
        return {"success": True, "keys": keys}
    except Exception as e:
        return {"success": False, "error": str(e)}


def desktop_get_windows() -> dict:
    """List all open windows on the desktop."""
    try:
        result = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            windows = []
            for line in result.stdout.strip().splitlines():
                parts = line.split(None, 3)
                if len(parts) >= 4:
                    windows.append({"id": parts[0], "title": parts[3]})
            return {"success": True, "source": "wmctrl", "windows": windows}
    except FileNotFoundError:
        pass

    try:
        result = subprocess.run(
            ["xdotool", "search", "--onlyvisible", "--name", ""],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            ids = result.stdout.strip().splitlines()
            return {"success": True, "source": "xdotool", "window_ids": ids}
    except FileNotFoundError:
        pass

    return {"success": False, "error": "Window list unavailable. Install: sudo apt install wmctrl"}
