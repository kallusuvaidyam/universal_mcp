#!/usr/bin/env python3
"""
Universal Dev MCP — Entry Point
Usage:
  python main.py start --project /path/to/project --port 8080
  python main.py setup
"""
import argparse
import os
import sys
import threading
import time
from pathlib import Path


def print_banner(project_path: str, port: int, local_url: str, tunnel_url: str = None):
    print("\n" + "="*55)
    print("  🚀 Universal Dev MCP")
    print("="*55)
    print(f"  Project : {project_path}")
    print(f"  Port    : {port}")
    print()
    print(f"  ✅ Local URL  : {local_url}")
    if tunnel_url:
        print(f"  ✅ Remote URL : {tunnel_url}")
    else:
        print(f"  ⚠  Remote URL : Not configured")
        print(f"     Run 'python setup_wizard.py' to setup Cloudflare tunnel")
    print()
    print("  Add in Claude.ai:")
    print("  Settings → Integrations → Custom MCP → Paste URL")
    print()
    print("  Press Ctrl+C to stop")
    print("="*55 + "\n")


def start_tunnel_async(port: int) -> tuple:
    """Start Cloudflare tunnel in background thread, return (proc, url)."""
    result = {"proc": None, "url": None}

    def _run():
        from tunnel import start_tunnel
        proc, url = start_tunnel(port)
        result["proc"] = proc
        result["url"] = url

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=25)  # Wait max 25s for URL
    return result["proc"], result["url"]


def cmd_start(args):
    project_path = os.path.abspath(args.project)
    port = args.port

    if not Path(project_path).is_dir():
        print(f"❌ Project path not found: {project_path}")
        sys.exit(1)

    os.environ["MCP_PROJECT_PATH"] = project_path

    local_url = f"http://localhost:{port}"
    tunnel_url = None
    tunnel_proc = None

    # Start cloudflare tunnel
    from config import load_global_config
    cfg = load_global_config()
    has_tunnel = cfg.get("tunnel_name") or cfg.get("use_quick_tunnel")

    if has_tunnel:
        print("\n  Starting Cloudflare tunnel... (please wait)")
        tunnel_proc, tunnel_url = start_tunnel_async(port)
        # If stable tunnel, URL is already in config
        if not tunnel_url and cfg.get("tunnel_url"):
            tunnel_url = cfg.get("tunnel_url")

    print_banner(project_path, port, local_url, tunnel_url)

    # Start MCP server (blocking)
    try:
        from server import run_server
        run_server(project_path, port)
    except KeyboardInterrupt:
        print("\n\n  Stopping Universal Dev MCP...")
        if tunnel_proc:
            tunnel_proc.terminate()
        print("  Bye! 👋\n")
        sys.exit(0)


def cmd_setup(args):
    import setup_wizard
    setup_wizard.run()


def main():
    parser = argparse.ArgumentParser(
        description="Universal Dev MCP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py start                              # Current dir, port 8080
  python main.py start --port 5000                 # Custom port
  python main.py start --project /home/bob/app     # Specific project
  python main.py setup                             # One-time setup wizard
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command")

    # start
    start_p = subparsers.add_parser("start", help="Start MCP server")
    start_p.add_argument("--project", default=os.getcwd(), help="Project path (default: current dir)")
    start_p.add_argument("--port", type=int, default=8080, help="Port number (default: 8080)")

    # setup
    subparsers.add_parser("setup", help="Run one-time setup wizard")

    args = parser.parse_args()

    if args.command == "setup":
        cmd_setup(args)
    elif args.command == "start":
        cmd_start(args)
    else:
        # No command → default start from current dir
        args.project = os.getcwd()
        args.port = 8080
        cmd_start(args)


if __name__ == "__main__":
    main()
