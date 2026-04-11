# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.
"""
✘ Commands Available -

• `{i}remind <waktu> <pesan>`
    Set pengingat. Waktu bisa: 30s, 10m, 2h, 1d
    Contoh: `.remind 30m Beli makan malam`

• `{i}reminders`
    Lihat semua pengingat yang aktif.

• `{i}cancelremind <id>`
    Batalkan pengingat berdasarkan ID.

• `{i}clearremind`
    Hapus semua pengingat yang aktif.
"""

import asyncio
import time
from datetime import datetime

from pyUltroid.fns.admins import ban_time

from . import udB, ultroid_bot, ultroid_cmd, LOGS

help_reminder = __doc__

# In-memory store: {task_id: (asyncio.Task, message, trigger_ts)}
_reminders: dict = {}
_counter = 0


def _parse_time(s: str) -> int:
    """Return seconds from strings like 30s, 10m, 2h, 1d. Returns 0 on parse failure."""
    s = s.strip().lower()
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    if s.isdigit():
        return int(s)
    if s[-1] in units:
        try:
            return int(s[:-1]) * units[s[-1]]
        except ValueError:
            return 0
    return 0


@ultroid_cmd(pattern="remind( (.*)|$)")
async def set_reminder(e):
    global _counter
    match = e.pattern_match.group(1).strip()
    if not match:
        return await e.eor(
            "`[REMIND] Penggunaan: .remind <waktu> <pesan>`\n"
            "`Contoh: .remind 30m Beli makan malam`"
        )

    parts = match.split(" ", 1)
    if len(parts) < 2:
        return await e.eor(
            "`[REMIND] Harap sertakan waktu dan pesan.`\n"
            "`Contoh: .remind 1h Ambil laundry`"
        )

    time_str, message = parts[0], parts[1]
    secs = _parse_time(time_str)

    if secs <= 0:
        return await e.eor(
            "`[REMIND] Format waktu tidak valid.`\n"
            "`Gunakan: 30s, 10m, 2h, 1d`"
        )

    if secs > 7 * 24 * 3600:
        return await e.eor("`[REMIND] Maksimum pengingat adalah 7 hari.`")

    _counter += 1
    rid = _counter
    trigger_ts = int(time.time()) + secs
    chat_id = e.chat_id
    msg_id = e.id

    async def _fire():
        await asyncio.sleep(secs)
        fire_time = datetime.now().strftime("%d %b %Y %H:%M:%S")
        try:
            await ultroid_bot.send_message(
                chat_id,
                f"⏰ **Pengingat #{rid}**\n\n{message}\n\n`Dijadwalkan: {fire_time}`",
                reply_to=msg_id,
            )
        except Exception as err:
            LOGS.warning(f"[REMIND] Gagal mengirim pengingat #{rid}: {err}")
        _reminders.pop(rid, None)

    task = asyncio.get_event_loop().create_task(_fire())
    _reminders[rid] = (task, message, trigger_ts)

    trigger_fmt = datetime.fromtimestamp(trigger_ts).strftime("%d %b %Y %H:%M:%S")
    await e.eor(
        f"`[REMIND] Pengingat #{rid} diset.`\n"
        f"**Pesan:** {message}\n"
        f"**Waktu:** `{trigger_fmt}`"
    )


@ultroid_cmd(pattern="reminders$")
async def list_reminders(e):
    if not _reminders:
        return await e.eor("`[REMIND] Tidak ada pengingat aktif.`")

    now = int(time.time())
    out = "**Pengingat Aktif:**\n\n"
    for rid, (_, msg, ts) in sorted(_reminders.items()):
        remaining = ts - now
        if remaining > 0:
            h, rem = divmod(remaining, 3600)
            m, s = divmod(rem, 60)
            time_left = f"{h}j {m}m {s}d" if h else f"{m}m {s}d"
        else:
            time_left = "segera"
        out += f"• **#{rid}** — `{msg[:50]}` — sisa `{time_left}`\n"

    await e.eor(out)


@ultroid_cmd(pattern="cancelremind( (.*)|$)")
async def cancel_reminder(e):
    match = e.pattern_match.group(1).strip()
    if not match or not match.isdigit():
        return await e.eor("`[REMIND] Contoh: .cancelremind 1`")

    rid = int(match)
    if rid not in _reminders:
        return await e.eor(f"`[REMIND] Pengingat #{rid} tidak ditemukan.`")

    task, msg, _ = _reminders.pop(rid)
    task.cancel()
    await e.eor(f"`[REMIND] Pengingat #{rid} (`{msg[:40]}`) dibatalkan.`")


@ultroid_cmd(pattern="clearremind$")
async def clear_reminders(e):
    if not _reminders:
        return await e.eor("`[REMIND] Tidak ada pengingat aktif.`")

    count = len(_reminders)
    for rid, (task, _, _) in list(_reminders.items()):
        task.cancel()
    _reminders.clear()
    await e.eor(f"`[REMIND] {count} pengingat dihapus.`")
