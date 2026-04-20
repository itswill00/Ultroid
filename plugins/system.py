
from . import get_help
__doc__ = get_help("system")

# Ultroid - System Management & Diagnostics
# Professional suite for monitoring and resource lifecycle.

import asyncio
import os
import platform
import random
import shutil
import time
from datetime import timedelta

from pyUltroid.dB._core import LIST
from pyUltroid.fns import some_random_headers
from pyUltroid.fns.helper import humanbytes, time_cache, time_formatter

from . import (
    HOSTED_ON,
    Var,
    asst,
    async_searcher,
    start_time,
    udB,
    ultroid_cmd,
    ultroid_version,
)

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False

# ========================= CONSTANTS =============================

CLEAN_DIRECTORIES = ["downloads", "temp", "cache"]
HEROKU_API = Var.HEROKU_API
HEROKU_APP_NAME = Var.HEROKU_APP_NAME

# ========================= HELPERS =============================

def _bar(percent: float, width: int = 12) -> str:
    filled = int(width * percent / 100)
    return "█" * filled + "░" * (width - filled)

def _proc_uptime() -> str:
    try:
        with open("/proc/uptime") as f:
            secs = float(f.read().split()[0])
        delta = timedelta(seconds=int(secs))
        h, rem = divmod(delta.seconds, 3600)
        m, s = divmod(rem, 60)
        return f"{delta.days}d {h}h {m}m {s}s"
    except Exception:
        return time_formatter((time.time() - start_time) * 1000)

@time_cache(ttl=15)
async def get_ram_pct():
    if _HAS_PSUTIL:
        return psutil.virtual_memory().percent
    try:
        def _read_mem():
            with open("/proc/meminfo", "r") as f:
                lines = f.readlines()
            total = available = 0
            for line in lines:
                if "MemTotal" in line:
                    total = int(line.split()[1])
                elif "MemAvailable" in line:
                    available = int(line.split()[1])
            return total, available

        mem_total, mem_available = await asyncio.to_thread(_read_mem)
        if mem_total > 0:
            return ((mem_total - mem_available) / mem_total) * 100
    except Exception:
        pass
    return 0

async def get_db_usage():
    try:
        total = 512 if udB.name == "Mongo" else 30 if udB.name == "Redis" else 20
        total_bytes = total * (2**20)
        used_bytes = udB.usage
        pct = (used_bytes / total_bytes) * 100
        return f"`{humanbytes(used_bytes)} / {humanbytes(total_bytes)}` ({pct:.1f}%)"
    except Exception:
        return "N/A"

async def get_heroku_quota():
    if HOSTED_ON != "heroku" or not (HEROKU_API and HEROKU_APP_NAME):
        return None
    try:
        import heroku3
        Heroku = heroku3.from_key(HEROKU_API)
        account_id = Heroku.account().id
        headers = {
            "User-Agent": random.choice(some_random_headers),
            "Authorization": f"Bearer {HEROKU_API}",
            "Accept": "application/vnd.heroku+json; version=3.account-quotas",
        }
        url = f"https://api.heroku.com/accounts/{account_id}/actions/get-quota"
        result = await async_searcher(url, headers=headers, re_json=True)
        remaining = (result["account_quota"] - result["quota_used"]) / 60
        pct = (remaining / (result["account_quota"] / 60)) * 100
        return f"`{int(remaining // 60)}h {int(remaining % 60)}m` ({pct:.1f}%)"
    except Exception:
        return "N/A"

def _tail_sync(filename, n_lines):
    if not os.path.exists(filename):
        return "Log file not found."
    bufsize = 8192
    with open(filename, "rb") as f:
        f.seek(0, os.SEEK_END)
        filesize = f.tell()
        pos = filesize
        lines = []
        while len(lines) <= n_lines and pos > 0:
            pos = max(0, pos - bufsize)
            f.seek(pos)
            chunk = f.read(filesize - pos)
            lines = chunk.splitlines()
            filesize = pos
        return b"\n".join(lines[-n_lines:]).decode("utf-8", errors="replace")

async def tail_log(filename, n_lines=20):
    return await asyncio.to_thread(_tail_sync, filename, n_lines)

def _perform_cleanup(min_age=0):
    cleaned = 0
    now = time.time()
    for folder in CLEAN_DIRECTORIES:
        if os.path.exists(folder):
            for f in os.listdir(folder):
                path = os.path.join(folder, f)
                try:
                    if now - os.path.getmtime(path) < min_age:
                        continue
                    size = os.path.getsize(path) if os.path.isfile(path) else 0
                    if os.path.isfile(path) or os.path.islink(path):
                        os.unlink(path)
                    elif os.path.isdir(path):
                        shutil.rmtree(path)
                    cleaned += size
                except Exception:
                    continue
    return cleaned

# ========================= TASKS =============================

async def auto_cleaner():
    while True:
        try:
            ram_usage = await get_ram_pct()
            min_age = 1800 if ram_usage < 85 else 300
            cleared = await asyncio.to_thread(_perform_cleanup, min_age)
            if ram_usage > 90 and cleared > 1024*1024:
                log_ch = udB.get_key("LOG_CHANNEL")
                if log_ch:
                    await asst.send_message(log_ch, f"⚠️ **High RAM Alert** ({ram_usage:.1f}%). Freed `{humanbytes(cleared)}`.")
        except Exception:
            pass
        await asyncio.sleep(3600)

# ========================= COMMANDS =============================

@ultroid_cmd(pattern="sys$")
async def system_vitals(e):
    """System Health & Resource Dashboard"""
    wait = await e.eor("`Gathering system vitals...`")
    if _HAS_PSUTIL:
        cpu_pct = psutil.cpu_percent(interval=0.1)
        mem_pct = psutil.virtual_memory().percent
        d_pct = psutil.disk_usage("/").percent
    else:
        cpu_pct = 0.0
        mem_pct = await get_ram_pct()
        d_pct = 0.0

    db_str = await get_db_usage()
    hk_str = await get_heroku_quota()
    plugin_count = sum(len(v) for v in LIST.values())
    uptime = _proc_uptime()

    res = (
        f"📊 **System Dashboard**\n"
        f"---"
        f"\n**CPU**   `{cpu_pct:>5.1f}%`  `{_bar(cpu_pct)}`"
        f"\n**RAM**   `{mem_pct:>5.1f}%`  `{_bar(mem_pct)}`"
        f"\n**Disk**  `{d_pct:>5.1f}%`  `{_bar(d_pct)}`"
        f"\n\n**Uptime:** `{uptime}`"
        f"\n**Plugins:** `{plugin_count}` Active"
        f"\n**Database:** {db_str}"
    )
    if hk_str:
        res += f"\n**Heroku:** {hk_str}"
    res += f"\n\n⚙️ `Ultroid {ultroid_version}`"
    await wait.edit(res)

@ultroid_cmd(pattern="sysinfo$")
async def system_info(e):
    """Detailed System Specifications"""
    un = platform.uname()
    text = (
        f"🖥️ **System Specifications**\n"
        f"---"
        f"\n**OS:** {un.system} {un.release}"
        f"\n**Arch:** `{un.machine}`"
        f"\n**Python:** `{platform.python_version()}`"
        f"\n**Engine:** `Ultroid {ultroid_version}`"
        f"\n**Host:** `{un.node}`"
    )
    await e.eor(text)

@ultroid_cmd(pattern="logs(?: (.+))?$")
async def sys_logs(e):
    """View optimized runtime logs"""
    n = 20
    if e.pattern_match.group(1):
        try:
            n = min(int(e.pattern_match.group(1)), 100)
        except ValueError:
            pass
    log_data = await tail_log("ultroid.log", n)
    await e.eor(f"**Recent Logs ({n} lines):**\n\n```\n{log_data}\n```")

@ultroid_cmd(pattern="cleanup$", fullsudo=True)
async def manual_cleanup(e):
    """Manual system cleanup"""
    ok = await e.eor("`Performing manual cleanup...`")
    cleaned = await asyncio.to_thread(_perform_cleanup)
    await ok.edit(f"Cleanup finished.\n**Space Freed:** `{humanbytes(cleaned)}`")

if not hasattr(udB, "_sys_task_started"):
    asyncio.get_event_loop().create_task(auto_cleaner())
    udB._sys_task_started = True
