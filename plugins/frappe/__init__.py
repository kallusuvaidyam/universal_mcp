from plugins.frappe.bench_ops import TOOLS as BENCH_TOOLS
from plugins.frappe.executor import TOOLS as EXECUTOR_TOOLS
from plugins.frappe.frappe_api import TOOLS as FRAPPE_API_TOOLS
from plugins.frappe.log_reader import TOOLS as LOG_TOOLS
from plugins.frappe.site_manager import TOOLS as SITE_TOOLS

TOOLS = {
    **SITE_TOOLS,
    **BENCH_TOOLS,
    **FRAPPE_API_TOOLS,
    **EXECUTOR_TOOLS,
    **LOG_TOOLS,
}
