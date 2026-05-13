import json
import time

import requests
from requests.exceptions import ConnectionError, RequestException, Timeout

from plugins.frappe.common import (
    SiteCredentials,
    ensure_bench_running,
    json_text,
    parse_json_input,
    resolve_context,
    validate_api_credentials,
    validate_site,
)
from plugins.frappe.bench_ops import frappe_bench_start


DOCTYPE_TYPES = {
    "regular": "Normal DocType — stores its own records",
    "single": "Single DocType — only one record exists",
    "child": "Child Table — embedded inside another DocType",
    "virtual": "Virtual DocType — not stored in database",
}


def _fieldname(label: str) -> str:
    import re

    name = label.lower().strip()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    return name.strip("_") or "field"


def _normalize_fields(fields: list[dict]) -> list[dict]:
    normalized = []
    for field in fields:
        entry = dict(field)
        if not entry.get("fieldname") and entry.get("label"):
            entry["fieldname"] = _fieldname(entry["label"])
        entry.setdefault("reqd", 0)
        normalized.append(entry)
    return normalized


def _request(site: str, creds: SiteCredentials, endpoint: str, method: str, request_params: dict | None, request_body: dict | None):
    if not endpoint.startswith("/"):
        endpoint = "/" + endpoint

    response = requests.request(
        method=method,
        url=f"http://localhost:{creds.port}{endpoint}",
        headers={
            "Authorization": f"token {creds.api_key}:{creds.api_secret}",
            "Host": site,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Expect": "",
        },
        params=request_params if method == "GET" else None,
        json=request_body if method != "GET" else None,
        timeout=30,
    )
    return endpoint, response


def frappe_api_call(
    project_path: str,
    endpoint: str,
    method: str = "GET",
    params_json: str = "",
    filters_json: str = "",
    fields_json: str = "",
    limit: int = 20,
    bench_id: str = "",
    site: str = "",
    confirmed: bool = False,
) -> str:
    ctx = resolve_context(project_path, bench_id=bench_id, site=site)
    site_error = validate_site(ctx.site)
    creds_error = validate_api_credentials(ctx)
    if site_error or creds_error:
        return json_text({"success": False, "error": site_error or creds_error})

    method = method.upper().strip()
    if method not in {"GET", "POST", "PUT", "DELETE"}:
        return json_text({"success": False, "error": f"Invalid HTTP method '{method}'."})

    if method == "DELETE" and not confirmed:
        return json_text(
            {
                "success": False,
                "blocked": True,
                "error": "DELETE blocked — confirmed=true pass karo agar actual delete chahiye.",
            }
        )

    try:
        params = parse_json_input(params_json, {})
        filters = parse_json_input(filters_json, [])
        fields = parse_json_input(fields_json, [])
    except json.JSONDecodeError as exc:
        return json_text({"success": False, "error": f"Invalid JSON input: {exc}"})

    docker_error = ensure_bench_running(ctx)
    if docker_error:
        return json_text({"success": False, **docker_error})

    request_params = {}
    request_body = None
    limit = max(1, min(int(limit), 100))

    if method == "GET":
        request_params.update(params or {})
        if filters:
            request_params["filters"] = json.dumps(filters)
        if fields:
            request_params["fields"] = json.dumps(fields)
        request_params["limit_page_length"] = limit
    else:
        request_body = dict(params or {})
        if filters:
            request_body["filters"] = filters
        if fields:
            request_body["fields"] = fields

    try:
        endpoint, response = _request(ctx.site, ctx.site_credentials, endpoint, method, request_params, request_body)
    except ConnectionError:
        start_result = json.loads(frappe_bench_start(project_path, bench_id=ctx.bench_id))
        if start_result.get("success"):
            time.sleep(30)
            try:
                endpoint, response = _request(ctx.site, ctx.site_credentials, endpoint, method, request_params, request_body)
            except ConnectionError:
                return json_text(
                    {
                        "success": False,
                        "site": ctx.site,
                        "endpoint": endpoint,
                        "error": "Site unreachable even after auto-start attempt.",
                        "bench_start_attempted": True,
                    }
                )
        else:
            return json_text(
                {
                    "success": False,
                    "site": ctx.site,
                    "endpoint": endpoint,
                    "error": "Site unreachable and bench auto-start failed.",
                    "bench_start_attempted": True,
                    "bench_start_result": start_result,
                }
            )
    except Timeout:
        return json_text({"success": False, "site": ctx.site, "endpoint": endpoint, "error": "Request timed out after 30 seconds."})
    except RequestException as exc:
        return json_text({"success": False, "site": ctx.site, "endpoint": endpoint, "error": f"Request failed: {exc}"})

    try:
        data = response.json()
    except Exception:
        data = {"raw": response.text[:2000]}

    success = response.status_code < 400
    payload = {
        "success": success,
        "bench_id": ctx.bench_id,
        "site": ctx.site,
        "endpoint": endpoint,
        "method": method,
        "status_code": response.status_code,
        "data": data if success else None,
        "error": None if success else f"HTTP {response.status_code}: {response.reason}",
        "warning": f"{method} operation modifies data." if method in {"POST", "PUT"} else None,
    }
    return json_text({key: value for key, value in payload.items() if value is not None})


def frappe_create_doctype(
    project_path: str,
    name: str,
    doctype_type: str,
    module: str,
    fields_json: str = "",
    bench_id: str = "",
    site: str = "",
    confirmed: bool = False,
) -> str:
    doctype_key = doctype_type.lower().strip()
    if doctype_key not in DOCTYPE_TYPES:
        return json_text({"success": False, "error": f"Invalid doctype_type '{doctype_type}'.", "valid_types": DOCTYPE_TYPES})

    try:
        fields = _normalize_fields(parse_json_input(fields_json, []))
    except json.JSONDecodeError as exc:
        return json_text({"success": False, "error": f"Invalid fields_json: {exc}"})

    ctx = resolve_context(project_path, bench_id=bench_id, site=site)
    site_error = validate_site(ctx.site)
    creds_error = validate_api_credentials(ctx)
    if site_error or creds_error:
        return json_text({"success": False, "error": site_error or creds_error})

    preview = {
        "name": name,
        "type": doctype_key,
        "type_description": DOCTYPE_TYPES[doctype_key],
        "module": module,
        "site": ctx.site,
        "bench_id": ctx.bench_id,
        "fields_count": len(fields),
        "fields": fields or "No fields — DocType will be created empty.",
    }

    if not confirmed:
        return json_text(
            {
                "success": False,
                "step": "confirmation_required",
                "preview": preview,
                "action": "Sab sahi lage to confirmed=true ke saath dobara call karo.",
            }
        )

    payload = {
        "doctype": "DocType",
        "name": name,
        "module": module,
        "issingle": 1 if doctype_key == "single" else 0,
        "istable": 1 if doctype_key == "child" else 0,
        "isvirtual": 1 if doctype_key == "virtual" else 0,
        "fields": fields,
        "permissions": [{"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1}],
    }
    return frappe_api_call(
        project_path=project_path,
        endpoint="/api/resource/DocType",
        method="POST",
        params_json=json.dumps(payload),
        bench_id=ctx.bench_id,
        site=ctx.site,
    )


TOOLS = {
    "frappe_api_call": {"fn": frappe_api_call, "description": "Make authenticated REST API calls to a Frappe site"},
    "frappe_create_doctype": {"fn": frappe_create_doctype, "description": "Preview or create a Frappe DocType"},
}
