from datetime import datetime, timedelta

from plugins.frappe.common import (
    classify_log_line,
    json_text,
    parse_timestamp,
    resolve_context,
    resolve_log_path,
    validate_bench_id,
    validate_site,
)


VALID_LOG_TYPES = {"error", "scheduler", "worker", "web", "bench"}


def frappe_get_logs(
    project_path: str,
    log_type: str = "error",
    lines: int = 50,
    filter_text: str = "",
    since_minutes: int = 0,
    bench_id: str = "",
    site: str = "",
) -> str:
    ctx = resolve_context(project_path, bench_id=bench_id, site=site)
    bench_error = validate_bench_id(ctx.bench_id)
    if bench_error:
        return json_text({"success": False, "error": bench_error})

    log_type = log_type.strip().lower()
    if log_type not in VALID_LOG_TYPES:
        return json_text({"success": False, "error": f"Invalid log_type '{log_type}'.", "valid_log_types": sorted(VALID_LOG_TYPES)})

    if log_type != "bench":
        site_error = validate_site(ctx.site)
        if site_error:
            return json_text({"success": False, "error": site_error})

    lines = max(1, min(int(lines), 200))
    log_path = resolve_log_path(ctx.bench_path, log_type, ctx.site)
    if not log_path.is_file():
        return json_text(
            {
                "success": False,
                "bench_id": ctx.bench_id,
                "site": ctx.site or None,
                "log_type": log_type,
                "error": f"Log file not found: {log_path}",
            }
        )

    raw_lines = log_path.read_text(errors="replace").splitlines()[-lines * 3 :]

    if since_minutes:
        cutoff = datetime.now() - timedelta(minutes=since_minutes)
        filtered_lines = []
        for line in raw_lines:
            ts = parse_timestamp(line)
            if ts is None or ts >= cutoff:
                filtered_lines.append(line)
        raw_lines = filtered_lines

    if filter_text:
        filtered = filter_text.lower()
        raw_lines = [line for line in raw_lines if filtered in line.lower()]

    raw_lines = raw_lines[-lines:]
    logs = []
    error_count = 0
    warning_count = 0

    for line in raw_lines:
        if not line.strip():
            continue
        level = classify_log_line(line)
        if level in {"ERROR", "CRITICAL"}:
            error_count += 1
        elif level == "WARNING":
            warning_count += 1
        logs.append({"line": line, "level": level})

    return json_text(
        {
            "success": True,
            "bench_id": ctx.bench_id,
            "site": ctx.site or None,
            "log_type": log_type,
            "log_file": str(log_path),
            "lines_returned": len(logs),
            "has_errors": error_count > 0,
            "error_count": error_count,
            "warning_count": warning_count,
            "filter_text": filter_text or None,
            "since_minutes": since_minutes or None,
            "logs": logs,
        }
    )


TOOLS = {
    "frappe_get_logs": {"fn": frappe_get_logs, "description": "Read Frappe site or bench log files"},
}
