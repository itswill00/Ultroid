# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.
"""
» Commands Available -


from . import get_help
__doc__ = get_help("help_update_monitor")

• `{i}upmonitor`
    Check the status of the automated update monitor.
"""

import asyncio
from datetime import datetime

from git import Repo
from telethon import Button

from pyUltroid.fns.helper import gen_chlog

from . import (
    LOG_CHANNEL,
    LOGS,
    asst,
    bash,
    callback,
    udB,
    ultroid_cmd,
)

_INTERVAL = 3600  # 1 Hour
_monitor_task = None
_UPSTREAM_REMOTE = "upstream"


async def check_for_updates():
    """Background loop to check for upstream commits."""
    while True:
        try:
            # 1. Fetch from upstream
            repo = Repo()
            if _UPSTREAM_REMOTE not in repo.remotes:
                # Add upstream if missing (standard Ultroid practice)
                repo.create_remote(_UPSTREAM_REMOTE, repo.remotes[0].url)

            ups_rem = repo.remote(_UPSTREAM_REMOTE)
            ac_br = repo.active_branch.name
            ups_rem.fetch(ac_br)

            # 2. Check diff
            changelog, tl_chnglog = await gen_chlog(repo, f"HEAD..{_UPSTREAM_REMOTE}/{ac_br}")

            if changelog:
                # 3. Deduplication Check
                latest_commit = str(repo.commit(f"{_UPSTREAM_REMOTE}/{ac_br}"))
                last_notified = udB.get_key("LAST_UPDATE_NOTIFICATION")

                if latest_commit != last_notified:
                    # 4. Notify via Assistant Bot
                    target = udB.get_key("LOG_CHANNEL") or LOG_CHANNEL
                    if target:
                        msg = (
                            f"🚀 **New Update Detected**\n"
                            f"Branch: `{ac_br}`\n"
                            f"Time: `{datetime.now().strftime('%H:%M:%S')}`\n\n"
                            f"{changelog[:3000]}\n\n"
                            f"💡 *Click the button below to update your system.*"
                        )
                        buttons = [
                            [
                                Button.inline("📥 Update Now", data="updatenow"),
                                Button.url("📂 View Repo", url=repo.remotes[0].url.replace(".git", "")),
                            ]
                        ]
                        try:
                            await asst.send_message(target, msg, buttons=buttons, parse_mode="html")
                            # Save state
                            udB.set_key("LAST_UPDATE_NOTIFICATION", latest_commit)
                            LOGS.info(f"UpdateMonitor | Notified new update: {latest_commit}")
                        except Exception as e:
                            LOGS.warning(f"UpdateMonitor | Notification failed: {e}")
        except Exception as er:
            LOGS.debug(f"UpdateMonitor | Silent Fail: {er}")

        await asyncio.sleep(_INTERVAL)


# Start the background task upon plugin load
if _monitor_task is None:
    _monitor_task = asyncio.get_event_loop().create_task(check_for_updates())


@ultroid_cmd(pattern="upmonitor$")
async def monitor_status(e):
    if _monitor_task and not _monitor_task.done():
        status = "✅ Active"
    else:
        status = "⭕ Inactive"

    last = udB.get_key("LAST_UPDATE_NOTIFICATION") or "None"
    await e.eor(
        f"**Update Monitor Status**\n"
        f"Status: {status}\n"
        f"Interval: `{_INTERVAL // 60} minutes`\n"
        f"Last Commit Notified: `{last[:10]}`"
    )


@callback("changes", owner=True)
async def view_changes(event):
    repo = Repo()
    ac_br = repo.active_branch.name
    changelog, _ = await gen_chlog(repo, f"HEAD..upstream/{ac_br}")
    if not changelog:
        return await event.answer("No new changes found.", alert=True)
    await event.edit(
        f"📋 **Detailed Changelog**\n\n{changelog[:3500]}",
        parse_mode="html",
        buttons=[[Button.inline("📥 Update Now", data="updatenow"), Button.inline("« Back", data="updtavail")]],
    )


@callback("updatenow", owner=True)
async def trigger_update(event):
    await event.edit("`Updating system... Please wait.`")
    # Trigger the update logic (pulling and restarting)
    await bash("git pull -f && pip3 install -r requirements.txt --break-system-packages -q")
    await event.edit("`Update complete! Restarting...`")
    await asyncio.sleep(2)
    from pyUltroid.fns.helper import restart
    await restart()