import json

import requests

_MAX_BODY = 20000


def http_request(project_path: str, url: str, method: str = "GET",
                 headers: str = "", body: str = "", timeout: int = 30) -> str:
    """Generic HTTP client for testing local endpoints. Returns status + headers + body."""
    if not url.startswith(("http://", "https://")):
        url = "http://" + url

    try:
        parsed_headers = json.loads(headers) if headers else {}
    except Exception:
        return "❌ headers must be valid JSON (e.g. '{\"Authorization\": \"token ...\"}')"

    kwargs = {"timeout": timeout, "headers": parsed_headers}
    if body:
        try:
            kwargs["json"] = json.loads(body)
        except Exception:
            kwargs["data"] = body

    try:
        resp = requests.request(method.upper(), url, **kwargs)
    except Exception as e:
        return f"❌ Request failed: {e}"

    out = [f"{method.upper()} {url}", f"Status: {resp.status_code} {resp.reason}"]
    out.append("Headers:")
    for k, v in resp.headers.items():
        out.append(f"  {k}: {v}")
    text = resp.text or ""
    if len(text) > _MAX_BODY:
        text = text[:_MAX_BODY] + "\n\n... [truncated]"
    out.append("\nBody:\n" + text)
    return "\n".join(out)
