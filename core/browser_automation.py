"""
Browser automation using Playwright.
Run 'playwright install chromium' once after pip install.
"""
from typing import Optional

_browser = None
_page = None


def _get_page():
    global _browser, _page
    if _page is None:
        from playwright.sync_api import sync_playwright
        pw = sync_playwright().start()
        _browser = pw.chromium.launch(headless=False)
        _page = _browser.new_page()
    return _page


def browser_navigate(url: str) -> str:
    try:
        page = _get_page()
        page.goto(url, timeout=30000)
        return f"✅ Navigated to: {url}\nTitle: {page.title()}"
    except Exception as e:
        return f"❌ Navigation error: {e}"


def browser_get_content() -> str:
    try:
        page = _get_page()
        text = page.inner_text("body")
        if len(text) > 8000:
            text = text[:8000] + "\n...[truncated]"
        return text
    except Exception as e:
        return f"❌ Error: {e}"


def browser_click(selector: str) -> str:
    try:
        page = _get_page()
        page.click(selector)
        return f"✅ Clicked: {selector}"
    except Exception as e:
        return f"❌ Click error: {e}"


def browser_type(selector: str, text: str) -> str:
    try:
        page = _get_page()
        page.fill(selector, text)
        return f"✅ Typed into: {selector}"
    except Exception as e:
        return f"❌ Type error: {e}"


def browser_screenshot() -> str:
    try:
        page = _get_page()
        path = "/tmp/mcp_screenshot.png"
        page.screenshot(path=path)
        return f"✅ Screenshot saved: {path}"
    except Exception as e:
        return f"❌ Screenshot error: {e}"


def browser_close() -> str:
    global _browser, _page
    try:
        if _browser:
            _browser.close()
            _browser = None
            _page = None
        return "✅ Browser closed"
    except Exception as e:
        return f"❌ Error: {e}"
