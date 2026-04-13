# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.
"""
» Commands Available -

• `{i}pingcheck`
    One-shot latency check to Telegram servers.

• `{i}pingwatch <interval> <limit>`
    Monitor latency every <interval> seconds for <limit> pings.
    Defaults: interval=10, limit=6 (1 minute total).
    Example: `.pingwatch 5 12`

• `{i}pingstop`
    Stop an active pingwatch session.
"""

import asyncio
import time
from datetime import datetime

from . import udB, ultroid_bot, ultroid_cmd, LOGS

help_ping_monitor = __doc__

_watch_task: asyncio.Task | None = None


def _latency_bar(ms: float) -> str:
    if ms < 100:
        return "🟢"
    elif ms < 300:
        return "🟡"
    else:
        return "🔴"


@ultroid_cmd(pattern="pingcheck$")
async def ping_check(e):
    t1 = time.perf_counter()
    msg = await e.eor("`Ping | Measuring latency...`")
    t2 = time.perf_counter()
    ms = round((t2 - t1) * 1000, 2)
    icon = _latency_bar(ms)
    await msg.edit(
        f"`Ping |` {icon} **{ms} ms**\n"
        f"`{datetime.now().strftime('%d %b %Y %H:%M:%S')}`"
    )


@ultroid_cmd(pattern="pingwatch( (.*)|$)")
async def ping_watch(e):
    global _watch_task

    if _watch_task and not _watch_task.done():
        return await e.eor(
            "`Ping | A watch session is already active. Use .pingstop to stop it.`"
        )

    match = e.pattern_match.group(1).strip().split()
    try:
        interval = max(5, int(match[0])) if match else 10
        limit = max(1, min(int(match[1]), 60)) if len(match) > 1 else 6
    except (ValueError, IndexError):
        interval, limit = 10, 6

    msg = await e.eor(
        f"`Ping | Starting watch: {limit} pings every {interval}s...`"
    )
    results = []

    async def _watcher():
        for i in range(limit):
            if _watch_task and _watch_task.cancelled():
                break
            t1 = time.perf_counter()
            try:
                await ultroid_bot.get_me()
            except Exception:
                pass
            ms = round((time.perf_counter() - t1) * 1000, 2)
            results.append(ms)
            lines = "\n".join(
                f"`{j+1:02d}.` {_latency_bar(r)} `{r} ms`"
                for j, r in enumerate(results)
            )
            avg = sum(results) / len(results)
            try:
                await msg.edit(
                    f"**Ping Watch** ({i+1}/{limit})\n\n{lines}\n\n"
                    f"**Avg:** `{avg:.1f} ms`"
                )
            except Exception:
                pass
            if i < limit - 1:
                await asyncio.sleep(interval)

        # Final summary
        if results:
            avg = sum(results) / len(results)
            mn, mx = min(results), max(results)
            try:
                await msg.edit(
                    f"**Ping Watch — Complete**\n\n"
                    f"**Samples:** `{len(results)}`\n"
                    f"**Min:** `{mn} ms` · **Max:** `{mx} ms` · **Avg:** `{avg:.1f} ms`"
                )
            except Exception:
                pass

    _watch_task = asyncio.get_event_loop().create_task(_watcher())


@ultroid_cmd(pattern="pingstop$")
async def ping_stop(e):
    global _watch_task
    if _watch_task and not _watch_task.done():
        _watch_task.cancel()
        _watch_task = None
        await e.eor("`Ping | Watch session stopped.`")
    else:
        await e.eor("`Ping | No active watch session.`")
