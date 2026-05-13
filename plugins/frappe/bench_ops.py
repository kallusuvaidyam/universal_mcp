import subprocess

from plugins.frappe.common import (
    background_start_command,
    ensure_bench_running,
    json_text,
    resolve_context,
    run_bench,
    summarize_output,
    validate_bench_id,
    validate_site,
)


def frappe_bench_restart(project_path: str, bench_id: str = "", target: str = "all") -> str:
    ctx = resolve_context(project_path, bench_id=bench_id)
    bench_error = validate_bench_id(ctx.bench_id)
    if bench_error:
        return json_text({"success": False, "error": bench_error})

    valid_targets = {"all", "web", "worker", "scheduler"}
    if target not in valid_targets:
        return json_text({"success": False, "error": f"Invalid target '{target}'.", "valid_targets": sorted(valid_targets)})

    docker_error = ensure_bench_running(ctx)
    if docker_error:
        return json_text({"success": False, **docker_error})

    subargs = ["restart"] if target == "all" else ["restart", target]
    try:
        result = run_bench(ctx, subargs, timeout=60)
    except ValueError as exc:
        return json_text({"success": False, "error": str(exc)})
    except subprocess.TimeoutExpired:
        return json_text({"success": False, "bench_id": ctx.bench_id, "target": target, "error": "Command timed out after 60 seconds."})
    except Exception as exc:
        return json_text({"success": False, "bench_id": ctx.bench_id, "target": target, "error": str(exc)})

    return json_text(
        {
            "success": result.returncode == 0,
            "bench_id": ctx.bench_id,
            "target": target,
            "output": result.stdout.strip() or None,
            "error": result.stderr.strip() or None,
            "return_code": result.returncode,
        }
    )


def frappe_bench_start(project_path: str, bench_id: str = "") -> str:
    ctx = resolve_context(project_path, bench_id=bench_id)
    bench_error = validate_bench_id(ctx.bench_id)
    if bench_error:
        return json_text({"success": False, "error": bench_error})

    docker_error = ensure_bench_running(ctx)
    if docker_error and "not running" not in docker_error.get("error", "").lower():
        return json_text({"success": False, **docker_error})

    cmd, log_file = background_start_command(ctx)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    except subprocess.TimeoutExpired:
        return json_text({"success": False, "bench_id": ctx.bench_id, "error": "bench start timed out after 20 seconds."})
    except Exception as exc:
        return json_text({"success": False, "bench_id": ctx.bench_id, "error": str(exc)})

    return json_text(
        {
            "success": result.returncode == 0,
            "bench_id": ctx.bench_id,
            "message": "bench start background me trigger kiya gaya." if result.returncode == 0 else None,
            "note": "Server ready hone me 20-40 seconds lag sakte hain." if result.returncode == 0 else None,
            "log_file": log_file if result.returncode == 0 else None,
            "output": result.stdout.strip() or None,
            "error": result.stderr.strip() or None,
            "return_code": result.returncode,
        }
    )


def frappe_bench_migrate(project_path: str, bench_id: str = "", site: str = "", force: bool = False) -> str:
    ctx = resolve_context(project_path, bench_id=bench_id, site=site)
    bench_error = validate_bench_id(ctx.bench_id)
    site_error = validate_site(ctx.site)
    if bench_error or site_error:
        return json_text({"success": False, "error": bench_error or site_error})

    docker_error = ensure_bench_running(ctx)
    if docker_error:
        return json_text({"success": False, **docker_error})

    subargs = ["--site", ctx.site, "migrate"]
    if force:
        subargs.append("--force")

    try:
        result = run_bench(ctx, subargs, timeout=300)
    except ValueError as exc:
        return json_text({"success": False, "error": str(exc)})
    except subprocess.TimeoutExpired:
        return json_text({"success": False, "bench_id": ctx.bench_id, "site": ctx.site, "error": "Migration timed out after 5 minutes."})
    except Exception as exc:
        return json_text({"success": False, "bench_id": ctx.bench_id, "site": ctx.site, "error": str(exc)})

    output_meta = summarize_output(result.stdout or "", result.stderr or "")
    payload = {
        "success": result.returncode == 0,
        "bench_id": ctx.bench_id,
        "site": ctx.site,
        "force": force,
        "output": output_meta["output"],
        "output_truncated": output_meta["output_truncated"],
        "total_output_lines": output_meta["total_output_lines"],
        "returned_output_lines": output_meta["returned_output_lines"],
        "return_code": result.returncode,
    }
    if result.returncode != 0:
        payload["error"] = output_meta["last_error_line"] or "Migration failed."
    return json_text(payload)


def frappe_bench_backup(project_path: str, bench_id: str = "", site: str = "", with_files: bool = False) -> str:
    ctx = resolve_context(project_path, bench_id=bench_id, site=site)
    bench_error = validate_bench_id(ctx.bench_id)
    site_error = validate_site(ctx.site)
    if bench_error or site_error:
        return json_text({"success": False, "error": bench_error or site_error})

    docker_error = ensure_bench_running(ctx)
    if docker_error:
        return json_text({"success": False, **docker_error})

    subargs = ["--site", ctx.site, "backup"]
    if with_files:
        subargs.append("--with-files")

    try:
        result = run_bench(ctx, subargs, timeout=180)
    except ValueError as exc:
        return json_text({"success": False, "error": str(exc)})
    except subprocess.TimeoutExpired:
        return json_text({"success": False, "bench_id": ctx.bench_id, "site": ctx.site, "error": "Backup timed out after 3 minutes."})
    except Exception as exc:
        return json_text({"success": False, "bench_id": ctx.bench_id, "site": ctx.site, "error": str(exc)})

    backup_file = None
    for line in (result.stdout + result.stderr).splitlines():
        if "backup" in line.lower() and (".sql" in line or ".gz" in line):
            for token in line.split():
                if ".sql" in token or ".gz" in token:
                    backup_file = token.strip()
                    break
            if backup_file:
                break

    return json_text(
        {
            "success": result.returncode == 0,
            "bench_id": ctx.bench_id,
            "site": ctx.site,
            "with_files": with_files,
            "backup_file": backup_file,
            "output": result.stdout.strip() or None,
            "error": result.stderr.strip() or None,
            "return_code": result.returncode,
        }
    )


def frappe_bench_build(project_path: str, bench_id: str = "", app: str = "") -> str:
    ctx = resolve_context(project_path, bench_id=bench_id)
    bench_error = validate_bench_id(ctx.bench_id)
    if bench_error:
        return json_text({"success": False, "error": bench_error})

    docker_error = ensure_bench_running(ctx)
    if docker_error:
        return json_text({"success": False, **docker_error})

    subargs = ["build"]
    if app:
        subargs += ["--app", app]

    try:
        result = run_bench(ctx, subargs, timeout=300)
    except ValueError as exc:
        return json_text({"success": False, "error": str(exc)})
    except subprocess.TimeoutExpired:
        return json_text({"success": False, "bench_id": ctx.bench_id, "app": app or "all", "error": "Build timed out after 5 minutes."})
    except Exception as exc:
        return json_text({"success": False, "bench_id": ctx.bench_id, "app": app or "all", "error": str(exc)})

    output_meta = summarize_output(result.stdout or "", result.stderr or "")
    payload = {
        "success": result.returncode == 0,
        "bench_id": ctx.bench_id,
        "app": app or "all",
        "output": output_meta["output"],
        "output_truncated": output_meta["output_truncated"],
        "total_output_lines": output_meta["total_output_lines"],
        "returned_output_lines": output_meta["returned_output_lines"],
        "return_code": result.returncode,
    }
    if result.returncode == 0:
        payload["message"] = f"Build complete for {app}." if app else "Build complete for all apps."
    else:
        payload["error"] = output_meta["last_error_line"] or f"Build failed (exit {result.returncode})."
    return json_text(payload)


def frappe_bench_setup_requirements(project_path: str, bench_id: str = "") -> str:
    ctx = resolve_context(project_path, bench_id=bench_id)
    bench_error = validate_bench_id(ctx.bench_id)
    if bench_error:
        return json_text({"success": False, "error": bench_error})

    docker_error = ensure_bench_running(ctx)
    if docker_error:
        return json_text({"success": False, **docker_error})

    try:
        result = run_bench(ctx, ["setup", "requirements"], timeout=600)
    except ValueError as exc:
        return json_text({"success": False, "error": str(exc)})
    except subprocess.TimeoutExpired:
        return json_text({"success": False, "bench_id": ctx.bench_id, "error": "bench setup requirements timed out after 10 minutes."})
    except Exception as exc:
        return json_text({"success": False, "bench_id": ctx.bench_id, "error": str(exc)})

    output_meta = summarize_output(result.stdout or "", result.stderr or "")
    payload = {
        "success": result.returncode == 0,
        "bench_id": ctx.bench_id,
        "output": output_meta["output"],
        "output_truncated": output_meta["output_truncated"],
        "total_output_lines": output_meta["total_output_lines"],
        "returned_output_lines": output_meta["returned_output_lines"],
        "return_code": result.returncode,
    }
    if result.returncode == 0:
        payload["message"] = "bench setup requirements complete."
    else:
        payload["error"] = output_meta["last_error_line"] or f"bench setup requirements failed (exit {result.returncode})."
    return json_text(payload)


TOOLS = {
    "frappe_bench_restart": {"fn": frappe_bench_restart, "description": "Restart Frappe bench services"},
    "frappe_bench_start": {"fn": frappe_bench_start, "description": "Start Frappe bench in background"},
    "frappe_bench_migrate": {"fn": frappe_bench_migrate, "description": "Run bench migrate for a site"},
    "frappe_bench_backup": {"fn": frappe_bench_backup, "description": "Create a Frappe site backup"},
    "frappe_bench_build": {"fn": frappe_bench_build, "description": "Run bench build for one app or all apps"},
    "frappe_bench_setup_requirements": {"fn": frappe_bench_setup_requirements, "description": "Run bench setup requirements"},
}
