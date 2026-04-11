# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.
"""
✘ Commands Available -

• `{i}sysmon`
    Tampilkan snapshot penggunaan CPU, RAM, disk, dan network saat ini.

• `{i}sysmon live`
    Mode live — update otomatis setiap 5 detik selama 30 detik.

• `{i}sysinfo`
    Informasi sistem lengkap: OS, Python, arsitektur, uptime.
"""

import asyncio
import os
import platform
import time
from datetime import datetime, timedelta

from . import udB, ultroid_cmd, LOGS

help_sysmon = __doc__

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False


def _bar(percent: float, width: int = 12) -> str:
    """Generate a simple ASCII progress bar."""
    filled = int(width * percent / 100)
    return "█" * filled + "░" * (width - filled)


def _fmt_bytes(b: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"


def _uptime() -> str:
    try:
        boot = psutil.boot_time()
        delta = timedelta(seconds=int(time.time() - boot))
        h, rem = divmod(delta.seconds, 3600)
        m, s = divmod(rem, 60)
        return f"{delta.days}d {h}h {m}m {s}s"
    except Exception:
        return "N/A"


def _build_snapshot() -> str:
    if not _HAS_PSUTIL:
        return "`[SYSMON] psutil tidak terinstal. Jalankan: pip install psutil`"

    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    try:
        net = psutil.net_io_counters()
        net_str = (
            f"↑ {_fmt_bytes(net.bytes_sent)}  ↓ {_fmt_bytes(net.bytes_recv)}"
        )
    except Exception:
        net_str = "N/A"

    sep = "─" * 30
    return (
        f"{sep}\n"
        f"⚙️ **System Monitor**\n"
        f"{sep}\n"
        f"**CPU**   `{cpu:5.1f}%`  `{_bar(cpu)}`\n"
        f"**RAM**   `{ram.percent:5.1f}%`  `{_bar(ram.percent)}`\n"
        f"         `{_fmt_bytes(ram.used)} / {_fmt_bytes(ram.total)}`\n"
        f"**Disk**  `{disk.percent:5.1f}%`  `{_bar(disk.percent)}`\n"
        f"         `{_fmt_bytes(disk.used)} / {_fmt_bytes(disk.total)}`\n"
        f"**Net**   `{net_str}`\n"
        f"**Up**    `{_uptime()}`\n"
        f"{sep}\n"
        f"`{datetime.now().strftime('%d %b %Y %H:%M:%S')}`"
    )


@ultroid_cmd(pattern="sysmon( (.*)|$)")
async def sys_monitor(e):
    match = e.pattern_match.group(1).strip()

    if match == "live":
        msg = await e.eor("`[SYSMON] Memulai mode live (30 detik)...`")
        for _ in range(6):  # 6 iterasi × 5 detik = 30 detik
            try:
                await msg.edit(_build_snapshot())
                await asyncio.sleep(5)
            except Exception:
                break
        try:
            await msg.edit(_build_snapshot() + "\n\n`[SYSMON] Sesi live selesai.`")
        except Exception:
            pass
    else:
        await e.eor(_build_snapshot())


@ultroid_cmd(pattern="sysinfo$")
async def sys_info(e):
    if not _HAS_PSUTIL:
        return await e.eor(
            "`[SYSINFO] psutil tidak terinstal. Jalankan: pip install psutil`"
        )

    uname = platform.uname()
    py_ver = platform.python_version()
    cpu_count = psutil.cpu_count(logical=True)
    cpu_freq = psutil.cpu_freq()
    freq_str = f"{cpu_freq.current:.0f} MHz" if cpu_freq else "N/A"
    boot_ts = datetime.fromtimestamp(psutil.boot_time()).strftime("%d %b %Y %H:%M:%S")

    sep = "─" * 30
    text = (
        f"{sep}\n"
        f"🖥️ **System Info**\n"
        f"{sep}\n"
        f"**OS**       `{uname.system} {uname.release}`\n"
        f"**Arch**     `{uname.machine}`\n"
        f"**Hostname** `{uname.node}`\n"
        f"**Python**   `{py_ver}`\n"
        f"**CPU**      `{cpu_count} core @ {freq_str}`\n"
        f"**Boot**     `{boot_ts}`\n"
        f"**Uptime**   `{_uptime()}`\n"
        f"{sep}"
    )
    await e.eor(text)
