from plugins.frappe.common import (
    discover_sites,
    get_installed_apps,
    get_site_port,
    json_text,
    load_frappe_config,
    ping_site,
    read_site_config,
    resolve_context,
    validate_bench_id,
    _find_bench_in_array,
    detect_bench_path,
    guess_bench_cmd,
    resolve_site_credentials,
    SiteCredentials,
    BenchContext,
)
from pathlib import Path


def _is_credentials_configured(site: str, site_credentials: dict) -> bool:
    """Check credentials with port-suffix tolerance.
    site='test.localhost' matches key 'test.localhost:8001' or 'test.localhost'."""
    if site in site_credentials:
        return True
    # Check if any key starts with site + ":"
    return any(k.startswith(site + ":") for k in site_credentials)


def _bench_ctx_from_cfg(project_path: str, config: dict, bench_cfg: dict) -> BenchContext:
    """Build a BenchContext directly from a benches[] entry."""
    bench_path = detect_bench_path(project_path, config, bench_cfg)
    return BenchContext(
        project_path=project_path,
        bench_id=bench_cfg.get("id", bench_path.name),
        bench_path=bench_path,
        bench_cmd=guess_bench_cmd(bench_path, config, bench_cfg),
        node_version=str(bench_cfg.get("node_version", "")).strip() or None,
        site="",
        site_credentials=SiteCredentials(),
        config=config,
    )


def frappe_list_sites(project_path: str, bench_id: str = "") -> str:
    """
    List all benches and their sites with installed apps and status.
    If bench_id given, show only that bench. Otherwise show all benches.
    Supports both multi-bench format (benches[] array) and flat format.
    """
    config = load_frappe_config(project_path)
    benches_list = config.get("benches")

    # ── Multi-bench mode (new format) ──
    if isinstance(benches_list, list) and benches_list:
        if bench_id:
            targets = [b for b in benches_list if isinstance(b, dict) and b.get("id") == bench_id]
            if not targets:
                return json_text({"success": False, "error": f"bench_id '{bench_id}' not found in config."})
        else:
            targets = [b for b in benches_list if isinstance(b, dict)]

        result_benches = []
        for bench_cfg in targets:
            ctx = _bench_ctx_from_cfg(project_path, config, bench_cfg)
            sites = []
            for site in discover_sites(ctx.bench_path):
                site_config = read_site_config(ctx.bench_path, site)
                port = get_site_port(ctx, site)
                sites.append({
                    "name": site,
                    "status": ping_site(site, port),
                    "installed_apps": get_installed_apps(ctx, site),
                    "db_name": site_config.get("db_name"),
                    "db_host": site_config.get("db_host", "localhost"),
                    "credentials_configured": _is_credentials_configured(site, config.get("site_credentials", {})),
                    "port": port,
                })
            result_benches.append({
                "id": ctx.bench_id,
                "label": bench_cfg.get("label", ctx.bench_id),
                "path": str(ctx.bench_path),
                "total_sites": len(sites),
                "sites": sites,
            })

        return json_text({
            "success": True,
            "total_benches": len(result_benches),
            "benches": result_benches,
        })

    # ── Single-bench mode (old flat format) ──
    ctx = resolve_context(project_path, bench_id=bench_id)
    bench_error = validate_bench_id(ctx.bench_id)
    if bench_error:
        return json_text({"success": False, "error": bench_error})

    sites = []
    for site in discover_sites(ctx.bench_path):
        site_config = read_site_config(ctx.bench_path, site)
        port = get_site_port(ctx, site)
        sites.append({
            "name": site,
            "status": ping_site(site, port),
            "installed_apps": get_installed_apps(ctx, site),
            "db_name": site_config.get("db_name"),
            "db_host": site_config.get("db_host", "localhost"),
            "credentials_configured": _is_credentials_configured(site, ctx.config.get("site_credentials", {})) or bool(site == ctx.site and ctx.site_credentials.api_key),
            "port": port,
        })

    return json_text({
        "success": True,
        "bench_id": ctx.bench_id,
        "bench_path": str(ctx.bench_path),
        "total_sites": len(sites),
        "sites": sites,
    })


TOOLS = {
    "frappe_list_sites": {"fn": frappe_list_sites, "description": "List all Frappe benches and their sites, apps, and status"},
}
