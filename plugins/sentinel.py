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
        f"╔════════ SYSTEM SENTINEL ════════╗\n"
        f"║ status : OPERATIONAL            ║\n"
        f"║ uptime : {uptime:<21} ║\n"
        f"╟─────────────────────────────────╢\n"
        f"║ cpu    : {cpu_usage:<21} ║\n"
        f"║ ram    : {mem_usage:<21} ║\n"
        f"║ db pt  : {db_latency:<17} ms ║\n"
        f"╟─────────────────────────────────╢\n"
        f"║ engine : Ultroid {ultroid_version:<13} ║\n"
        f"║ env    : {sys_name} / {py_ver:<11} ║\n"
        f"║ active : {plugin_count:<4} plugins           ║\n"
        f"╚═════════════════════════════════╝"
    )

    await ult.eor(f"`{card}`")

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
