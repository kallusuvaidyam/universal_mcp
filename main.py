#!/usr/bin/env python3
"""
Universal Dev MCP — Entry Point
Usage:
  python3 main.py start                              # Auto-detect project from registry
  python3 main.py start --project /path/to/project  # Specific project
  python3 main.py start --port 5000                 # Custom port
  python3 main.py setup                             # One-time setup wizard
  python3 main.py status                            # Show current server state
"""
import argparse
import os
import sys
import threading
from pathlib import Path


def _check_deps():
    try:
        import uvicorn  # noqa: F401
        import mcp  # noqa: F401
    except ImportError:
        import shutil
        py310 = shutil.which("python3.10")
        if py310 and py310 != sys.executable:
            os.execv(py310, [py310] + sys.argv)
        sys.exit("❌ Missing dependencies. Run: pip install -r requirements.txt")

_check_deps()


def _resolve_project(explicit_path: str | None) -> str:
    """
    Priority:
      1. Explicit --project flag
      2. Last active path from state.json
      3. First registered project in config
      4. Current working directory
    """
    from config import load_global_config, load_state

    if explicit_path:
        return os.path.abspath(explicit_path)

    state = load_state()
    if state.get("active_project_path") and Path(state["active_project_path"]).exists():
        return state["active_project_path"]

    cfg = load_global_config()
    projects = cfg.get("projects", [])
    if projects and Path(projects[0]["path"]).exists():
        return projects[0]["path"]

    return os.getcwd()


def print_banner(project_path: str, port: int, plugins: list, tunnel_url: str = None):
    print("\n" + "=" * 55)
    print("  Universal Dev MCP")
    print("=" * 55)
    print(f"  Project : {project_path}")
    print(f"  Port    : {port}")
    print(f"  Plugins : {', '.join(plugins)}")
    print()
    print(f"  Local URL  : http://localhost:{port}/mcp")
    if tunnel_url:
        print(f"  Remote URL : {tunnel_url}/mcp")
    else:
        print(f"  Remote URL : Not configured (run setup_wizard.py)")
    print()
    print("  Claude.ai: Settings → Integrations → Custom MCP → Paste Remote URL")
    print("  Press Ctrl+C to stop")
    print("=" * 55 + "\n")


def start_tunnel_async(port: int) -> tuple:
    result = {"proc": None, "url": None}

    def _run():
        from tunnel import start_tunnel
        proc, url = start_tunnel(port)
        result["proc"] = proc
        result["url"] = url

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=25)
    return result["proc"], result["url"]


def cmd_start(args):
    from config import load_global_config

    # jab user ne --project and project path diya hai to wahi use hoga, agar nahi diya to last active project ya first registered project ya current working directory use hoga.
    project_path = _resolve_project(getattr(args, "project", None))

    if not Path(project_path).is_dir():
        print(f"❌ Project path not found: {project_path}")
        sys.exit(1)

    # agar user ne --port diya hai to wahi use hoga, agar nahi diya to global config me default_port key ka value use hoga, agar global config me default_port key nahi hai to 8080 use hoga.
    port = getattr(args, "port", None) or load_global_config().get("default_port", 8080)
    # project_path ko environment variable me store karte hain taaki server.py isse padh sake.
    # server.py startup pe PROJECT_PATH = os.environ.get("MCP_PROJECT_PATH", os.getcwd()) karta hai,
    # yaani yahi active project ban jaata hai. main.py se server.py tak path pahunchane ka bridge.
    os.environ["MCP_PROJECT_PATH"] = project_path

    cfg = load_global_config()
    plugins = cfg.get("active_plugins", ["generic"])
    tunnel_url = None
    tunnel_proc = None

    provider = cfg.get("tunnel_provider", "none")
    if provider not in ("none", "local_only"):
        print(f"\n  Starting {provider} tunnel... (please wait)")
        tunnel_proc, tunnel_url = start_tunnel_async(port)
        if not tunnel_url:
            tunnel_url = cfg.get("tunnel_url")

    print_banner(project_path, port, plugins, tunnel_url)

    try:
        from server import run_server
        run_server(project_path, port)
    except KeyboardInterrupt:
        print("\n\n  Stopping Universal Dev MCP...")
        if tunnel_proc:
            tunnel_proc.terminate()
        print("  Bye!\n")
        sys.exit(0)


def cmd_setup(args):
    import setup_wizard
    setup_wizard.run()


def cmd_status(args):
    from config import load_global_config, load_state
    cfg = load_global_config()
    state = load_state()

    print("\n" + "=" * 55)
    print("  Universal Dev MCP — Status")
    print("=" * 55)
    print(f"  Active project : {state.get('active_project_path', 'Not set')}")
    print(f"  Tunnel         : {cfg.get('tunnel_provider', 'none')} — {cfg.get('tunnel_url', 'no URL')}")
    print(f"  Active plugins : {', '.join(cfg.get('active_plugins', ['generic']))}")
    print()
    projects = cfg.get("projects", [])
    if projects:
        print("  Registered projects:")
        for p in projects:
            marker = " <-- active" if p["path"] == state.get("active_project_path") else ""
            print(f"    • {p['name']:15} [{p['framework']:10}] {p['path']}{marker}")
    else:
        print("  No projects registered. Run setup_wizard.py")
    print("=" * 55 + "\n")


def main():
    parser = argparse.ArgumentParser(
        # jab ham python3 main.py --help command chalate hai to description sabse top par show hota hai
        description="Universal Dev MCP",
        # jaise epilog me new-lines, spaces, Indentations etc hai same vaise hi rakhne ke liye formatter_class ka use hota hai agar ye nahi hota to sab one line me hi show honge.
        formatter_class=argparse.RawDescriptionHelpFormatter, 
        # Epi = End(help ke sabse last me)
        epilog=""" 
            Examples:
            python main.py start                          # Auto-detect project, start server
            python main.py start --project /home/me/app  # Specific project
            python main.py start --port 5000             # Custom port
            python main.py setup                         # One-time setup wizard
            python main.py status                        # Show config & active project
            """
        )

    # Program me multiple commands (start, setup, status) define karne ke liye.
    # User jo command run karega, uska naam args.command me save hoga.
    # Agar command registered nahi hai, to argparse automatically error dega.
    subparsers = parser.add_subparsers(dest="command")


    # "start" naam ki command register karta hai.
    start_p = subparsers.add_parser("start", help="Start MCP server")

    # Start command ke liye optional project path.
    # User "--project" na de to value None rahegi.
    start_p.add_argument(
        "--project",
        default=None,
        help="Project path (default: last active or first registered)"
    )

    # Start command ke liye optional port number.
    # type=int ki wajah se sirf integer value accept hogi.
    start_p.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port (default: 8080 or config)"
    )

    # Baaki commands register kar rahe hain.
    subparsers.add_parser("setup", help="Run one-time setup wizard")
    subparsers.add_parser("status", help="Show current config and active project")


    args = parser.parse_args()

    if args.command == "setup":
        cmd_setup(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "start":
        cmd_start(args)
    else:
        cmd_start(args)


if __name__ == "__main__":
    main()
