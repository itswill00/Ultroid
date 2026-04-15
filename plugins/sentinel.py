# Ultroid - System Sentinel
# Professional Health Monitoring

import time
import os
import platform
from . import ultroid_bot, asst, udB, HNDLR, ultroid_version
from pyUltroid._misc._decorators import ultroid_cmd
from pyUltroid.fns.helper import time_formatter, humanbytes

@ultroid_cmd(pattern="health$")
async def _health_cmd(ult):
    """System Health Sentinel"""
    start_time = time.time()
    
    # Calculate Uptime
    try:
        from pyUltroid import start_time as bot_start_time
        uptime = time_formatter((time.time() - bot_start_time) * 1000)
    except ImportError:
        uptime = "unknown"

    # DB Latency Check
    db_start = time.time()
    udB.ping()
    db_latency = round((time.time() - db_start) * 1000, 2)

    # System Stats
    sys_name = platform.system()
    node_name = platform.node()
    py_ver = platform.python_version()
    
    # Process Memory (Basic Fallback)
    try:
        import psutil
        process = psutil.Process(os.getpid())
        mem_usage = humanbytes(process.memory_info().rss)
        cpu_usage = f"{psutil.cpu_percent()}%"
    except ImportError:
        mem_usage = "N/A (psutil missing)"
        cpu_usage = "N/A"

    # Count loaded plugins
    from pyUltroid.dB._core import LIST
    plugin_count = sum(len(v) for v in LIST.values())

    # Build Dashboard Card
    card = (
        f"📡 **System Status**\n"
        f"---"
        f"\n⌛ **Uptime:** {uptime}"
        f"\n🚨 **Status:** Running"
        f"\n\n🧠 **Memory:** {mem_usage}"
        f"\n📊 **CPU:** {cpu_usage}"
        f"\n⚡ **Latency:** {db_latency}ms"
        f"\n\n⚙️ **Engine:** Ultroid {ultroid_version}"
        f"\n🖥️ **Env:** {sys_name} / {py_ver}"
        f"\n🧩 **Active:** {plugin_count} plugins"
    )

    await ult.eor(card)

@ultroid_cmd(pattern="syslog(?: (.+))?$")
async def _syslog_cmd(ult):
    """Fetch Bot Runtime Logs"""
    if not os.path.exists("ultroid.log"):
        return await ult.eor("`Log file not found.`")
    
    lines = 20
    if ult.pattern_match.group(1):
        try:
            lines = int(ult.pattern_match.group(1))
        except ValueError:
            pass

    with open("ultroid.log", "r") as f:
        log_data = f.readlines()
    
    last_logs = "".join(log_data[-lines:])
    await ult.eor(f"**Recent Logs:**\n\n```\n{last_logs}\n```")
