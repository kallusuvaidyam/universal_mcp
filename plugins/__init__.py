"""
Plugin loader — loads framework-specific tools based on .mcp-config.json
"""
import importlib

PLUGIN_MAP = {
    "android": "plugins.android",
    "angular": "plugins.angular",
    "aws": "plugins.aws",
    "cloud": "plugins.cloud",
    "django": "plugins.django",
    "docker": "plugins.docker",
    "fastapi": "plugins.fastapi",
    "flask": "plugins.flask",
    "flutter": "plugins.flutter",
    "frappe": "plugins.frappe",
    "generic": "plugins.generic",
    "laravel": "plugins.laravel",
    "llm": "plugins.llm",
    "mongodb": "plugins.mongodb",
    "mysql": "plugins.mysql",
    "next": "plugins.nextjs",
    "nextjs": "plugins.nextjs",
    "node": "plugins.node",
    "nodejs": "plugins.node",
    "nuxt": "plugins.nuxt",
    "nuxtjs": "plugins.nuxt",
    "playwright": "plugins.playwright",
    "postgres": "plugins.postgres",
    "postgresql": "plugins.postgres",
    "rag": "plugins.rag",
    "react": "plugins.react",
    "react-native": "plugins.react_native",
    "react_native": "plugins.react_native",
    "spring": "plugins.springboot",
    "spring-boot": "plugins.springboot",
    "springboot": "plugins.springboot",
    "vscode": "plugins.vscode",
    "vue": "plugins.vue",
}


def load_plugin_tools(framework: str) -> dict:
    """Load generic tools plus framework-specific tools."""
    framework = framework.lower().strip()

    try:
        generic_tools = getattr(importlib.import_module("plugins.generic"), "TOOLS", {})
    except Exception as e:
        print(f"  Warning: Plugin load error (plugins.generic): {e}")
        generic_tools = {}

    module_path = PLUGIN_MAP.get(framework)
    if not module_path or module_path == "plugins.generic":
        return generic_tools

    try:
        module = importlib.import_module(module_path)
        framework_tools = getattr(module, "TOOLS", {})
        return {**generic_tools, **framework_tools}
    except Exception as e:
        print(f"  Warning: Plugin load error ({module_path}): {e}")
        return generic_tools
