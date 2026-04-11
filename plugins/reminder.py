# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.
"""
» Commands Available -

• `{i}remind <time> <message>`
    Set a reminder. Time formats: 30s, 10m, 2h, 1d
    Example: `.remind 30m Buy dinner`

• `{i}reminders`
    List all active reminders.

• `{i}cancelremind <id>`
    Cancel a reminder by its ID.

• `{i}clearremind`
    Cancel all active reminders.
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
            "`[REMIND] Usage: .remind <time> <message>`\n"
            "`Example: .remind 30m Buy dinner`"
        )

    parts = match.split(" ", 1)
    if len(parts) < 2:
        return await e.eor(
            "`[REMIND] Please provide both a time and a message.`\n"
            "`Example: .remind 1h Pick up laundry`"
        )

    time_str, message = parts[0], parts[1]
    secs = _parse_time(time_str)

    if secs <= 0:
        return await e.eor(
            "`[REMIND] Invalid time format.`\n"
            "`Use: 30s, 10m, 2h, 1d`"
        )

    if secs > 7 * 24 * 3600:
        return await e.eor("`[REMIND] Maximum reminder duration is 7 days.`")

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
                f"⏰ **Reminder #{rid}**\n\n{message}\n\n`Triggered at: {fire_time}`",
                reply_to=msg_id,
            )
        except Exception as err:
            LOGS.warning(f"[REMIND] Failed to send reminder #{rid}: {err}")
        _reminders.pop(rid, None)

    task = asyncio.get_event_loop().create_task(_fire())
    _reminders[rid] = (task, message, trigger_ts)

    trigger_fmt = datetime.fromtimestamp(trigger_ts).strftime("%d %b %Y %H:%M:%S")
    await e.eor(
        f"`[REMIND] Reminder #{rid} set.`\n"
        f"**Message:** {message}\n"
        f"**Trigger:** `{trigger_fmt}`"
    )


@ultroid_cmd(pattern="reminders$")
async def list_reminders(e):
    if not _reminders:
        return await e.eor("`[REMIND] No active reminders.`")

    now = int(time.time())
    out = "**Active Reminders:**\n\n"
    for rid, (_, msg, ts) in sorted(_reminders.items()):
        remaining = ts - now
        if remaining > 0:
            h, rem = divmod(remaining, 3600)
            m, s = divmod(rem, 60)
            time_left = f"{h}h {m}m {s}s" if h else f"{m}m {s}s"
        else:
            time_left = "imminent"
        out += f"• **#{rid}** — `{msg[:50]}` — in `{time_left}`\n"

    await e.eor(out)


@ultroid_cmd(pattern="cancelremind( (.*)|$)")
async def cancel_reminder(e):
    match = e.pattern_match.group(1).strip()
    if not match or not match.isdigit():
        return await e.eor("`[REMIND] Example: .cancelremind 1`")

    rid = int(match)
    if rid not in _reminders:
        return await e.eor(f"`[REMIND] Reminder #{rid} not found.`")

    task, msg, _ = _reminders.pop(rid)
    task.cancel()
    await e.eor(f"`[REMIND] Reminder #{rid} ('{msg[:40]}') cancelled.`")


@ultroid_cmd(pattern="clearremind$")
async def clear_reminders(e):
    if not _reminders:
        return await e.eor("`[REMIND] No active reminders.`")

    count = len(_reminders)
    for rid, (task, _, _) in list(_reminders.items()):
        task.cancel()
    _reminders.clear()
    await e.eor(f"`[REMIND] {count} reminder(s) cleared.`")
