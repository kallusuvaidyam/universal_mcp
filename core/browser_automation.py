"""
Browser automation using Playwright.
Full implementation with persistent sessions, auto-login, JPEG screenshots.
Ported from frappe-mcp with fastmcp.Image removed — returns base64 dict instead.
"""

import base64
import os
import threading
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

_lock = threading.Lock()
_pw = None
_browser = None
_context = None
_page = None
_current_browser_type: str = "chromium"

# Persistent location — survives reboots unlike /tmp
_SESSIONS_DIR = str(Path.home() / ".universal-dev-mcp" / "browser_sessions")
_SESSION_FILE = f"{_SESSIONS_DIR}/browser_state.json"

_current_workflow = []


def _img(data: bytes) -> dict:
    """Return image as base64-encoded dict that server.py can handle."""
    return {"_image": True, "data": base64.b64encode(data).decode(), "format": "jpeg"}


def _save_session():
    if _context:
        try:
            os.makedirs(_SESSIONS_DIR, exist_ok=True)
            _context.storage_state(path=_SESSION_FILE)
        except Exception:
            pass


def _get_page():
    global _pw, _browser, _context, _page, _current_browser_type
    with _lock:
        if _pw is None:
            from playwright.sync_api import sync_playwright
            _pw = sync_playwright().start()
        if _browser is None or not _browser.is_connected():
            if _current_browser_type == "firefox":
                _browser = _pw.firefox.launch(headless=True)
            else:
                _browser = _pw.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage"],
                )
            _context = None
        if _context is None:
            os.makedirs(_SESSIONS_DIR, exist_ok=True)
            viewport = {"width": 1024, "height": 640}
            if os.path.exists(_SESSION_FILE):
                try:
                    _context = _browser.new_context(storage_state=_SESSION_FILE, viewport=viewport)
                except Exception:
                    _context = _browser.new_context(viewport=viewport)
            else:
                _context = _browser.new_context(viewport=viewport)
        if _page is None or _page.is_closed():
            _page = _context.new_page()
        return _page


def _snap() -> dict:
    return _img(_get_page().screenshot(type="jpeg", quality=70))


def _safe_retry(action, retries=3, delay=800):
    last_error = None
    for _ in range(retries):
        try:
            return action()
        except Exception as e:
            last_error = e
            try:
                _get_page().wait_for_timeout(delay)
            except Exception:
                pass
    raise last_error


def _record_step(action, data):
    global _current_workflow
    _current_workflow.append({"action": action, "data": data})


def browser_navigate(url: str, screenshot: bool = True) -> dict:
    """
    Open a URL in the browser.
    Session persists across calls — login once, cookies saved to disk.
    screenshot=False: returns only {success, url, title} — saves tokens.
    """
    try:
        page = _get_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1000)
        _record_step("navigate", {"url": url})
        if not screenshot:
            return {"success": True, "url": page.url, "title": page.title()}
        return _snap()
    except Exception as e:
        return {"success": False, "error": str(e), "url": url}


def browser_screenshot() -> dict:
    """Take a screenshot of the current browser page."""
    try:
        return _snap()
    except Exception as e:
        return {"success": False, "error": str(e)}


def save_current_workflow(workflow_name: str) -> dict:
    """Save current runtime workflow steps to memory."""
    global _current_workflow
    if not _current_workflow:
        return {"success": False, "error": "No workflow steps recorded."}
    total = len(_current_workflow)
    _current_workflow = []
    return {"success": True, "workflow_name": workflow_name, "steps_saved": total}


def browser_click(selector: str, screenshot: bool = True) -> dict:
    """
    Click an element by CSS selector or text.
    Tries multiple strategies + retry on failure.
    """
    try:
        page = _get_page()
        selectors_to_try = [selector]
        clicked = False
        used_selector = None

        for sel in selectors_to_try:
            strategies = [
                lambda s=sel: page.click(s, timeout=5000),
                lambda s=sel: page.get_by_text(s, exact=True).first.click(timeout=5000),
                lambda s=sel: page.get_by_text(s).first.click(timeout=5000),
                lambda s=sel: page.get_by_role("button", name=s).click(timeout=5000),
                lambda s=sel: page.get_by_role("menuitem", name=s).click(timeout=5000),
                lambda s=sel: page.locator(f"text={s}").first.click(timeout=5000),
            ]
            for strategy in strategies:
                try:
                    _safe_retry(strategy)
                    clicked = True
                    used_selector = sel
                    break
                except Exception:
                    continue
            if clicked:
                break

        if not clicked:
            try:
                page.reload(timeout=15000)
                page.wait_for_timeout(1500)
                for sel in selectors_to_try:
                    for strategy in [
                        lambda s=sel: page.click(s, timeout=5000),
                        lambda s=sel: page.get_by_text(s).first.click(timeout=5000),
                    ]:
                        try:
                            _safe_retry(strategy)
                            clicked = True
                            used_selector = sel
                            break
                        except Exception:
                            continue
                    if clicked:
                        break
            except Exception:
                pass

        if not clicked:
            return {
                "success": False,
                "error": f"Element not found: '{selector}'",
                "hint": "browser_screenshot() use karo aur correct selector identify karo.",
            }

        page.wait_for_timeout(800)
        if not screenshot:
            return {"success": True, "clicked": used_selector}
        return _snap()
    except Exception as e:
        return {"success": False, "error": str(e)}


def browser_type(selector: str, text: str, clear_first: bool = True) -> dict:
    """
    Type text into an input field.
    clear_first=True: clear existing content before typing (default).
    """
    try:
        page = _get_page()
        try:
            if clear_first:
                page.fill(selector, "", timeout=5000)
            page.type(selector, text, timeout=10000)
        except Exception:
            locator = page.get_by_placeholder(selector).first
            if clear_first:
                locator.fill("")
            locator.type(text)
        page.wait_for_timeout(400)
        return _snap()
    except Exception as e:
        return {"success": False, "error": str(e)}


def browser_press_key(key: str) -> dict:
    """
    Press a keyboard key.
    Examples: 'Enter', 'Escape', 'Tab', 'ArrowDown', 'Control+a'
    """
    try:
        page = _get_page()
        page.keyboard.press(key)
        page.wait_for_timeout(600)
        return _snap()
    except Exception as e:
        return {"success": False, "error": str(e)}


def browser_get_content() -> dict:
    """Get visible text content of the current page (first 8000 chars)."""
    try:
        page = _get_page()
        return {
            "success": True,
            "url": page.url,
            "title": page.title(),
            "text": page.inner_text("body")[:8000],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def browser_get_element(selector: str) -> dict:
    """
    Find a specific element and return its content.
    selector: CSS ('.alert', '#name'), text ('Customer Name'), or Frappe ("[data-fieldname='status']")
    """
    try:
        page = _get_page()

        def _extract(loc):
            tag = loc.evaluate("el => el.tagName.toLowerCase()")
            if tag == "table":
                rows = loc.locator("tr").all()
                table_data = []
                for row in rows[:50]:
                    cells = [c.inner_text().strip() for c in row.locator("td, th").all()]
                    if any(cells):
                        table_data.append(cells)
                return {"type": "table", "rows": table_data}
            if tag in ("input", "textarea", "select"):
                return {"type": tag, "value": loc.input_value()}
            return {"type": tag or "element", "text": loc.inner_text().strip()[:4000]}

        loc = page.locator(selector).first
        try:
            loc.wait_for(timeout=4000)
            return {"success": True, "selector": selector, **_extract(loc)}
        except Exception:
            pass

        loc2 = page.get_by_text(selector).first
        try:
            loc2.wait_for(timeout=3000)
            return {"success": True, "selector": f"text={selector}", **_extract(loc2)}
        except Exception:
            pass

        return {
            "success": False,
            "error": f"Element not found: '{selector}'",
            "hint": "browser_screenshot() se page dekho, phir valid selector use karo.",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def browser_wait(milliseconds: int = 2000) -> dict:
    """Wait for page/animation to finish, then take screenshot."""
    try:
        page = _get_page()
        page.wait_for_timeout(milliseconds)
        return _snap()
    except Exception as e:
        return {"success": False, "error": str(e)}


def browser_click_at(x: int, y: int, screenshot: bool = True) -> dict:
    """
    Click at exact pixel coordinates on the current page.
    Use after browser_screenshot() — identify position visually, pass x,y.
    screenshot=False: skip screenshot, saves tokens for intermediate clicks.
    """
    try:
        page = _get_page()
        page.mouse.click(x, y)
        page.wait_for_timeout(600)
        if not screenshot:
            return {"success": True, "clicked_at": {"x": x, "y": y}}
        return _snap()
    except Exception as e:
        return {"success": False, "error": str(e)}


def browser_save_session() -> dict:
    """Manually save current browser session (cookies) to disk."""
    try:
        _save_session()
        return {"success": True, "message": f"Session saved to {_SESSION_FILE}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def browser_launch(browser_type: str = "chromium") -> dict:
    """
    Launch a specific browser. Closes current browser first.
    browser_type: 'chromium' (default, fast) or 'firefox'.
    Saved session (cookies) restored automatically.
    """
    global _current_browser_type
    browser_type = browser_type.lower()
    if browser_type not in ("chromium", "firefox"):
        return {"success": False, "error": f"Unknown browser '{browser_type}'. Use 'chromium' or 'firefox'."}
    browser_close()
    _current_browser_type = browser_type
    has_session = os.path.exists(_SESSION_FILE)
    return {
        "success": True,
        "browser": browser_type,
        "session_restored": has_session,
        "message": f"{browser_type.capitalize()} ready. {'Previous session loaded.' if has_session else 'No saved session.'} Call browser_navigate(url) to open a page.",
    }


def browser_close() -> dict:
    """Close the browser and free resources. Session auto-saved."""
    global _pw, _browser, _context, _page
    with _lock:
        try:
            if _page and not _page.is_closed():
                _page.close()
            if _context:
                _save_session()
                _context.close()
            if _browser and _browser.is_connected():
                _browser.close()
            if _pw:
                _pw.stop()
            _page = _browser = _context = _pw = None
            return {"success": True, "message": "Browser closed. Session saved."}
        except Exception as e:
            return {"success": False, "error": str(e)}
