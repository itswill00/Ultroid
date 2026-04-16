# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.
"""
» Commands Available -

• `{i}sysmon`
    Show a snapshot of current CPU, RAM, disk, and network usage.

• `{i}sysmon live`
    Live mode — auto-updates every 5 seconds for 30 seconds.

• `{i}sysinfo`
    Full system information: OS, Python version, architecture, uptime.

NOTE: Works with or without psutil. On Mobile versions, install via:
  pkg install python-psutil
"""

import asyncio
import os
import platform
import time
from datetime import datetime, timedelta

from . import udB, ultroid_cmd, LOGS, asst_cmd

help_sysmon = __doc__

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False


# Helper: human-readable bytes
def _fmt_bytes(b: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"


def _bar(percent: float, width: int = 12) -> str:
    """Generate a simple ASCII progress bar."""
    filled = int(width * percent / 100)
    return "█" * filled + "░" * (width - filled)


# /proc-based fallbacks

def _proc_uptime() -> str:
    """Read system uptime from /proc/uptime (works on Termux)."""
    try:
        with open("/proc/uptime") as f:
            secs = float(f.read().split()[0])
        delta = timedelta(seconds=int(secs))
        h, rem = divmod(delta.seconds, 3600)
        m, s = divmod(rem, 60)
        return f"{delta.days}d {h}h {m}m {s}s"
    except Exception:
        return "N/A"


def _proc_cpu() -> float:
    """Estimate CPU usage by sampling /proc/stat over 0.5 seconds."""
    def _read_stat():
        try:
            with open("/proc/stat") as f:
                line = f.readline()  # first line: "cpu ..."
            vals = list(map(int, line.split()[1:]))
            idle = vals[3]
            total = sum(vals)
            return idle, total
        except Exception:
            return 0, 1

    idle1, total1 = _read_stat()
    time.sleep(0.5)
    idle2, total2 = _read_stat()
    d_total = total2 - total1
    d_idle = idle2 - idle1
    if d_total == 0:
        return 0.0
    return round((1 - d_idle / d_total) * 100, 1)


def _proc_mem() -> tuple[float, int, int]:
    """Return (percent_used, used_bytes, total_bytes) from /proc/meminfo."""
    try:
        info = {}
        with open("/proc/meminfo") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    info[parts[0].rstrip(":")] = int(parts[1]) * 1024
        total = info.get("MemTotal", 0)
        avail = info.get("MemAvailable", info.get("MemFree", 0))
        used = total - avail
        pct = (used / total * 100) if total else 0
        return round(pct, 1), used, total
    except Exception:
        return 0.0, 0, 0


def _proc_net() -> tuple[int, int]:
    """Return (bytes_sent, bytes_recv) from /proc/net/dev."""
    sent, recv = 0, 0
    try:
        with open("/proc/net/dev") as f:
            for line in f:
                parts = line.split()
                if len(parts) < 10 or parts[0].startswith(("lo:", "Inter", "face")):
                    continue
                recv += int(parts[1])
                sent += int(parts[9])
    except Exception:
        pass
    return sent, recv


def _disk_usage() -> tuple[float, int, int]:
    """Return (percent_used, used_bytes, total_bytes) via os.statvfs."""
    try:
        st = os.statvfs("/")
        total = st.f_blocks * st.f_frsize
        free = st.f_bavail * st.f_frsize
        used = total - free
        pct = (used / total * 100) if total else 0
        return round(pct, 1), used, total
    except Exception:
        return 0.0, 0, 0


# Main snapshot builder

def _build_snapshot() -> str:
    if _HAS_PSUTIL:
        # psutil path (more accurate)
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory()
        ram_pct, ram_used, ram_total = ram.percent, ram.used, ram.total
        disk_st = psutil.disk_usage("/")
        disk_pct, disk_used, disk_total = disk_st.percent, disk_st.used, disk_st.total
        try:
            net = psutil.net_io_counters()
            net_str = f"↑ {_fmt_bytes(net.bytes_sent)}  ↓ {_fmt_bytes(net.bytes_recv)}"
        except Exception:
            net_str = "N/A"
        uptime = _proc_uptime()
    else:
        # /proc fallback (Low-resource mode)
        cpu = _proc_cpu()
        ram_pct, ram_used, ram_total = _proc_mem()
        disk_pct, disk_used, disk_total = _disk_usage()
        s, r = _proc_net()
        net_str = f"↑ {_fmt_bytes(s)}  ↓ {_fmt_bytes(r)}"
        uptime = _proc_uptime()

    mode = "psutil" if _HAS_PSUTIL else "/proc"
    return (
        f"📊 **System Monitor** `({mode})`\n"
        f"---"
        f"\n**CPU**   `{cpu:>5.1f}%`  `{_bar(cpu)}`"
        f"\n**RAM**   `{ram_pct:>5.1f}%`  `{_bar(ram_pct)}`"
        f"\n         `{_fmt_bytes(ram_used)} / {_fmt_bytes(ram_total)}`"
        f"\n**Disk**  `{disk_pct:>5.1f}%`  `{_bar(disk_pct)}`"
        f"\n         `{_fmt_bytes(disk_used)} / {_fmt_bytes(disk_total)}`"
        f"\n**Net**   `{net_str}`"
        f"\n**Up**    `{uptime}`"
        f"\n\n⏱️ `{datetime.now().strftime('%d %b %Y %H:%M:%S')}`"
    )


# Commands

@asst_cmd(pattern="sysmon")
@ultroid_cmd(pattern="sysmon( (.*)|$)")
async def sys_monitor(e):
    match = e.pattern_match.group(1).strip()

    if match == "live":
        msg = await e.eor("`Sysmon | Starting live mode (30 seconds)...`")
        for _ in range(6):  # 6 × 5s = 30s
            try:
                await msg.edit(_build_snapshot())
                await asyncio.sleep(5)
            except Exception:
                break
        try:
            await msg.edit(_build_snapshot() + "\n\n`Sysmon | Live session ended.`")
        except Exception:
            pass
    else:
        await e.eor(_build_snapshot())


@asst_cmd(pattern="sysinfo")
@ultroid_cmd(pattern="sysinfo$")
async def sys_info(e):
    uname = platform.uname()
    py_ver = platform.python_version()
    uptime = _proc_uptime()

    # CPU count from /proc or psutil
    cpu_count = "N/A"
    cpu_freq = "N/A"
    boot_ts = "N/A"
    try:
        if _HAS_PSUTIL:
            cpu_count = str(psutil.cpu_count(logical=True))
            f = psutil.cpu_freq()
            cpu_freq = f"{f.current:.0f} MHz" if f else "N/A"
            boot_ts = datetime.fromtimestamp(psutil.boot_time()).strftime("%d %b %Y %H:%M:%S")
        else:
            # Count CPU cores from /proc/cpuinfo
            with open("/proc/cpuinfo") as f:
                cpu_count = str(f.read().count("processor\t:"))
            with open("/proc/uptime") as f:
                secs = float(f.read().split()[0])
            boot_dt = datetime.fromtimestamp(time.time() - secs)
            boot_ts = boot_dt.strftime("%d %b %Y %H:%M:%S")
    except Exception:
        pass

    backend = "psutil" if _HAS_PSUTIL else "/proc (Low-resource mode)"
    text = (
        f"🖥️ **System Info**\n"
        f"---"
        f"\n**OS**       {uname.system} {uname.release}"
        f"\n**Arch**     `{uname.machine}`"
        f"\n**Hostname** `{uname.node}`"
        f"\n**Python**   `{py_ver}`"
        f"\n**CPU**      {cpu_count} core(s) @ {cpu_freq}"
        f"\n**Boot**     `{boot_ts}`"
        f"\n**Uptime**   `{uptime}`"
        f"\n\n⚙️ **Backend:** `{backend}`"
    )
    await e.eor(text)
