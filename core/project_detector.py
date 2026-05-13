import json
from pathlib import Path


SIGNATURES = [
    {
        "framework": "frappe",
        "signals": [
            {"path": "apps/frappe",      "is_dir": True,  "score": 50},
            {"path": "sites",            "is_dir": True,  "score": 30},
            {"path": "apps/erpnext",     "is_dir": True,  "score": 20},
        ],
        "threshold": 50,
    },
    {
        "framework": "django",
        "signals": [
            {"path": "manage.py",        "is_dir": False, "score": 40},
            {"path": "requirements.txt", "is_dir": False, "score": 20, "contains": "Django"},
            {"path": "settings.py",      "is_dir": False, "score": 20},
            {"path": "urls.py",          "is_dir": False, "score": 20},
        ],
        "threshold": 40,
    },
    {
        "framework": "nextjs",
        "signals": [
            {"path": "next.config.js",   "is_dir": False, "score": 50},
            {"path": "next.config.ts",   "is_dir": False, "score": 50},
            {"path": "package.json",     "is_dir": False, "score": 20, "contains": '"next"'},
        ],
        "threshold": 50,
    },
    {
        "framework": "nuxt",
        "signals": [
            {"path": "nuxt.config.js",   "is_dir": False, "score": 50},
            {"path": "nuxt.config.ts",   "is_dir": False, "score": 50},
            {"path": "package.json",     "is_dir": False, "score": 20, "contains": '"nuxt"'},
        ],
        "threshold": 50,
    },
    {
        "framework": "laravel",
        "signals": [
            {"path": "artisan",          "is_dir": False, "score": 50},
            {"path": "composer.json",    "is_dir": False, "score": 30, "contains": "laravel/framework"},
            {"path": "app/Http",         "is_dir": True,  "score": 20},
        ],
        "threshold": 50,
    },
    {
        "framework": "flutter",
        "signals": [
            {"path": "pubspec.yaml",     "is_dir": False, "score": 40, "contains": "flutter:"},
            {"path": "lib/main.dart",    "is_dir": False, "score": 40},
            {"path": "android",          "is_dir": True,  "score": 20},
        ],
        "threshold": 50,
    },
    {
        "framework": "react",
        "signals": [
            {"path": "package.json",     "is_dir": False, "score": 20, "contains": '"react"'},
            {"path": "src/App.jsx",      "is_dir": False, "score": 40},
            {"path": "src/App.tsx",      "is_dir": False, "score": 40},
            {"path": "src/App.js",       "is_dir": False, "score": 40},
        ],
        "threshold": 40,
    },
    {
        "framework": "rust",
        "signals": [
            {"path": "Cargo.toml",       "is_dir": False, "score": 60},
            {"path": "src/main.rs",      "is_dir": False, "score": 40},
        ],
        "threshold": 60,
    },
    {
        "framework": "go",
        "signals": [
            {"path": "go.mod",           "is_dir": False, "score": 60},
            {"path": "main.go",          "is_dir": False, "score": 40},
        ],
        "threshold": 60,
    },
    {
        "framework": "rails",
        "signals": [
            {"path": "Gemfile",          "is_dir": False, "score": 30, "contains": "rails"},
            {"path": "config/routes.rb", "is_dir": False, "score": 40},
            {"path": "app/controllers",  "is_dir": True,  "score": 30},
        ],
        "threshold": 60,
    },
]


def _check_signal(root: Path, signal: dict) -> int:
    target = root / signal["path"]
    if signal["is_dir"]:
        if not target.is_dir():
            return 0
    else:
        if not target.is_file():
            return 0

    # Optional content check
    if "contains" in signal and target.is_file():
        try:
            content = target.read_text(errors="ignore")
            if signal["contains"] not in content:
                return 0
        except Exception:
            return 0

    return signal["score"]


def detect_framework(project_path: str) -> list[dict]:
    """
    Returns list of detected frameworks sorted by confidence score.
    Each entry: {"framework": str, "score": int, "confidence": str}
    """
    root = Path(project_path)
    results = []

    for sig in SIGNATURES:
        total = sum(_check_signal(root, s) for s in sig["signals"])
        max_possible = sum(s["score"] for s in sig["signals"])
        if total >= sig["threshold"]:
            pct = int((total / max_possible) * 100)
            confidence = "HIGH" if pct >= 80 else "MEDIUM" if pct >= 50 else "LOW"
            results.append({
                "framework": sig["framework"],
                "score": total,
                "confidence": confidence,
                "percent": pct,
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def format_detection_message(project_path: str) -> str:
    """Format detection result as a Claude-friendly message for confirmation."""
    results = detect_framework(project_path)

    if not results:
        return (
            "🔍 Project scan complete.\n\n"
            "Koi known framework detect nahi hua.\n\n"
            "Kya aap manually batana chahenge?\n"
            "Options:\n"
            "  1. Django\n  2. Next.js\n  3. Laravel\n  4. React\n"
            "  5. Rust\n  6. Go\n  7. Ruby on Rails\n  8. Generic/Other\n\n"
            "Reply karein: 'framework <naam>' (e.g. 'framework django')\n"
            "Ya 'generic' agar koi specific framework nahi hai."
        )

    top = results[0]
    others = results[1:]

    msg = f"🔍 Project scan complete.\n\n"
    msg += f"✅ Detected: **{top['framework'].upper()}** ({top['confidence']} confidence - {top['percent']}%)\n"

    if others:
        msg += f"\nOther matches: " + ", ".join(f"{r['framework']} ({r['percent']}%)" for r in others) + "\n"

    msg += f"\nKya ye sahi hai?\n"
    msg += f"  • 'yes' — confirm karo\n"
    msg += f"  • 'no' — manual batao\n"
    msg += f"  • 'framework <naam>' — different framework specify karo"

    return msg
