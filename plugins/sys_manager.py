"""
» Commands Available -

• `{i}cleanup`
    Perform a manual cleanup of temporary files in downloads, temp, and cache folders.

• `{i}sysstats`
    Retrieve detailed Termux system information including battery status, uptime, disk usage, and database type.

**Automated Feature:**
- Background Auto-Cleaner: Automatically clears temporary files older than 30 minutes every hour.
"""

import os
import shutil
import time
import asyncio
from . import ultroid_cmd, udB, eor, HNDLR, LOGS, start_time
from pyUltroid.fns.helper import time_formatter, humanbytes, time_cache

# List of folders to clean
CLEAN_DIRECTORIES = ["downloads", "temp", "cache"]

@time_cache(ttl=15)
async def get_ram_usage():
    """Retrieve memory usage percentage via /proc/meminfo (Linux/Termux)."""
    try:
        with open("/proc/meminfo", "r") as f:
            lines = f.readlines()
        mem_total = mem_available = 0
        for line in lines:
            if "MemTotal" in line:
                mem_total = int(line.split()[1])
            elif "MemAvailable" in line:
                mem_available = int(line.split()[1])
        if mem_total > 0:
            return ((mem_total - mem_available) / mem_total) * 100
    except Exception:
        pass
    return 0

async def auto_cleaner():
    """Background task to clean temporary files and monitor RAM."""
    while True:
        try:
            min_age_seconds = 1800  # Default: 30 minutes
            ram_usage = await get_ram_usage()
            is_emergency = False

            # Adaptive Threshold
            if ram_usage > 85:
                is_emergency = True
                min_age_seconds = 300  # Aggressive: 5 minutes if RAM is high
                LOGS.warning(f"Adaptive Resource Manager: High RAM ({ram_usage:.1f}%). Triggering cleanup completed.")

            now = time.time()
            cleared_size = 0
            for folder in CLEAN_DIRECTORIES:
                if os.path.exists(folder):
                    for filename in os.listdir(folder):
                        file_path = os.path.join(folder, filename)
                        try:
                            if now - os.path.getmtime(file_path) < min_age_seconds:
                                continue
                            
                            size = os.path.getsize(file_path) if os.path.isfile(file_path) else 0
                            if os.path.isfile(file_path) or os.path.islink(file_path):
                                os.unlink(file_path)
                            elif os.path.isdir(file_path):
                                shutil.rmtree(file_path)
                            cleared_size += size
                        except Exception:
                            continue
            
            if is_emergency and cleared_size > 1024 * 1024:
                try:
                    from pyUltroid import asst, udB
                    log_ch = udB.get_key("LOG_CHANNEL")
                    if log_ch:
                        await asst.send_message(
                            log_ch,
                            f"⚠️ **High Memory Alert**\n"
                            f"RAM usage critically high: `{ram_usage:.1f}%`.\n"
                            f"System performed an cleanup completed, freeing `{humanbytes(cleared_size)}`."
                        )
                except Exception:
                    pass
            elif not is_emergency:
                LOGS.info("System Auto-Cleanup: Temporary files cleared quietly.")

        except Exception as e:
            LOGS.error(f"Auto-Cleanup Error: {e}")

        await asyncio.sleep(3600 if not is_emergency else 600) # Check more frequently if in emergency

@ultroid_cmd(pattern="cleanup$", fullsudo=True)
async def manual_cleanup(e):
    """Manual cleanup of temp files."""
    ok = await eor(e, "`Starting system cleanup...`")
    cleaned = 0
    for folder in CLEAN_DIRECTORIES:
        if os.path.exists(folder):
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                try:
                    size = os.path.getsize(file_path)
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                    cleaned += size
                except Exception:
                    continue
    await ok.edit(f"Cleanup completed.\n**Space Freed:** `{humanbytes(cleaned)}`")

@ultroid_cmd(pattern="sysstats$", fullsudo=True)
async def system_stats(e):
    """Get Termux system information."""
    # Battery info (Termux specific)
    battery = "N/A"
    try:
        # Using standard Linux path available in Android/Termux
        with open("/sys/class/power_supply/battery/capacity", "r") as f:
            level = f.read().strip()
        with open("/sys/class/power_supply/battery/status", "r") as f:
            status = f.read().strip()
        battery = f"{level}% ({status})"
    except Exception:
        battery = "Unavailable"

    uptime = time_formatter((time.time() - start_time) * 1000)
    
    # RAM usage
    total, used, free = shutil.disk_usage(".")
    
    msg = f"🖥 **System Monitor**\n\n"
    msg += f"🔋 **Battery**: `{battery}`\n"
    msg += f"⏱ **Uptime**: `{uptime}`\n"
    msg += f"💽 **Disk Used**: `{humanbytes(used)} / {humanbytes(total)}`\n"
    msg += f"🧠 **RAM Load**: `{await get_ram_usage():.1f}%`\n"
    msg += f"📁 **DB Type**: `LocalDB (JSON)`\n"
    
    await eor(e, msg)

# Start background cleaner if not already running
if not hasattr(udB, "_cleaner_started"):
    try:
        import asyncio as _asyncio
        loop = _asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(auto_cleaner())
        else:
            _asyncio.ensure_future(auto_cleaner())
    except Exception:
        pass  # Will be skipped gracefully if no event loop is available at import time
    udB._cleaner_started = True
