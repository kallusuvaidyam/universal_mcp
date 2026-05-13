import subprocess

from plugins.frappe.common import (
    build_execute_method,
    ensure_bench_running,
    json_text,
    resolve_context,
    run_bench,
    scan_expression,
    try_parse_output,
    validate_bench_id,
    validate_site,
)


def frappe_execute(
    project_path: str,
    expression: str,
    bench_id: str = "",
    site: str = "",
    timeout: int = 30,
    confirmed: bool = False,
) -> str:
    ctx = resolve_context(project_path, bench_id=bench_id, site=site)
    bench_error = validate_bench_id(ctx.bench_id)
    site_error = validate_site(ctx.site)
    if bench_error or site_error:
        return json_text({"success": False, "error": bench_error or site_error})

    if not expression.strip():
        return json_text({"success": False, "error": "expression required hai."})

    timeout = max(1, min(int(timeout), 120))
    scan = scan_expression(ctx, expression)
    if scan.get("blocked"):
        return json_text(
            {
                "success": False,
                "blocked": True,
                "block_reason": scan["block_reason"],
                "expression": expression,
            }
        )

    if scan.get("warning") and not confirmed:
        return json_text(
            {
                "success": False,
                "step": "confirmation_required",
                "warning": scan["warning"],
                "expression": expression,
                "action": "Aage badhne ke liye confirmed=true ke saath dobara call karo.",
            }
        )

    docker_error = ensure_bench_running(ctx)
    if docker_error:
        return json_text({"success": False, **docker_error})

    try:
        result = run_bench(ctx, ["--site", ctx.site, "execute", build_execute_method(expression)], timeout=timeout)
    except ValueError as exc:
        return json_text({"success": False, "error": str(exc)})
    except subprocess.TimeoutExpired:
        return json_text(
            {
                "success": False,
                "bench_id": ctx.bench_id,
                "site": ctx.site,
                "expression": expression,
                "error": f"Expression timed out after {timeout} seconds.",
            }
        )
    except Exception as exc:
        return json_text({"success": False, "bench_id": ctx.bench_id, "site": ctx.site, "error": str(exc)})

    success = result.returncode == 0
    raw_output = result.stdout.strip()
    payload = {
        "success": success,
        "bench_id": ctx.bench_id,
        "site": ctx.site,
        "expression": expression,
        "result": try_parse_output(raw_output) if success and raw_output else None,
        "raw_output": raw_output or None,
        "error": (result.stderr.strip() or None) if not success else None,
        "warning": scan.get("warning"),
        "return_code": result.returncode,
    }
    return json_text({key: value for key, value in payload.items() if value is not None})


TOOLS = {
    "frappe_execute": {"fn": frappe_execute, "description": "Run Python inside a Frappe site context with safety checks"},
}
