# Ultroid - System Management Plugin
# Optimized for Termux by itswill00

import os
import shutil
import time
import asyncio
from . import ultroid_cmd, udB, eor, HNDLR, LOGS, start_time
from pyUltroid.fns.helper import time_formatter, humanbytes

# List of folders to clean
CLEAN_DIRECTORIES = ["downloads", "temp", "cache"]

async def auto_cleaner():
    """Background task to clean temporary files every hour."""
    while True:
        try:
            min_age_seconds = 1800  # Only delete files older than 30 minutes
            now = time.time()
            for folder in CLEAN_DIRECTORIES:
                if os.path.exists(folder):
                    for filename in os.listdir(folder):
                        file_path = os.path.join(folder, filename)
                        try:
                            # Skip files that are too new (might be in use)
                            if now - os.path.getmtime(file_path) < min_age_seconds:
                                continue
                            if os.path.isfile(file_path) or os.path.islink(file_path):
                                os.unlink(file_path)
                            elif os.path.isdir(file_path):
                                shutil.rmtree(file_path)
                        except Exception:
                            continue
            LOGS.info("System Auto-Cleanup: Temporary files cleared.")
        except Exception as e:
            LOGS.error(f"Auto-Cleanup Error: {e}")

        await asyncio.sleep(3600) # Clean every 1 hour

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
    await ok.edit(f"✅ **Cleanup Success!**\n**Space Freed:** `{humanbytes(cleaned)}`")

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
    
    msg = f"🖥 **Termux System Monitor**\n\n"
    msg += f"🔋 **Battery**: `{battery}`\n"
    msg += f"⏱ **Uptime**: `{uptime}`\n"
    msg += f"💽 **Disk Used**: `{humanbytes(used)} / {humanbytes(total)}`\n"
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
