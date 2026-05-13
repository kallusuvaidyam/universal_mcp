from plugins.frappe.common import (
    discover_sites,
    get_installed_apps,
    get_site_port,
    json_text,
    ping_site,
    read_site_config,
    resolve_context,
    validate_bench_id,
)


def frappe_list_sites(project_path: str, bench_id: str = "") -> str:
    ctx = resolve_context(project_path, bench_id=bench_id)
    bench_error = validate_bench_id(ctx.bench_id)
    if bench_error:
        return json_text({"success": False, "error": bench_error})

    sites = []
    for site in discover_sites(ctx.bench_path):
        site_config = read_site_config(ctx.bench_path, site)
        port = get_site_port(ctx, site)
        sites.append(
            {
                "name": site,
                "status": ping_site(site, port),
                "installed_apps": get_installed_apps(ctx, site),
                "db_name": site_config.get("db_name"),
                "db_host": site_config.get("db_host", "localhost"),
                "credentials_configured": bool(
                    (
                        isinstance(ctx.config.get("site_credentials"), dict)
                        and site in ctx.config.get("site_credentials", {})
                    )
                    or (site == ctx.site and ctx.site_credentials.api_key and ctx.site_credentials.api_secret)
                ),
                "port": port,
            }
        )

    return json_text(
        {
            "success": True,
            "bench_id": ctx.bench_id,
            "bench_path": str(ctx.bench_path),
            "total_sites": len(sites),
            "sites": sites,
        }
    )


TOOLS = {
    "frappe_list_sites": {"fn": frappe_list_sites, "description": "List Frappe sites, apps, and status"},
}
