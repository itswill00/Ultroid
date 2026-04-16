"""
★ Assistant-Exclusive Relay Module ★

This module acts as a silent proxy.
Commands like .dl, .yta, and .ytv are captured here on the userbot side
and instantly relayed to the Assistant Bot to process the actual download,
keeping your main account clean and unaffected.
"""

# Ultroid - UserBot
# Media Downloader Relay (Assistant Proxy)

import re

from pyUltroid import asst
from . import ultroid_cmd


@ultroid_cmd(pattern="(dl|yta|ytv)( (.*)|$)")
async def userbot_dl_relay(event):
    """Relays download commands to the Assistant Bot."""
    if not asst:
        return await event.edit("`[!] Assistant Bot is not active. Start the assistant to use downloaders.`", time=8)

    cmd = event.pattern_match.group(1)
    # group(3) captures only the URL part (without leading space)
    raw = event.pattern_match.group(3) or ""
    url = raw.strip()

    if not url:
        return await event.edit(f"`Usage: .{cmd} <link>`", time=5)

    # Validate URL before relaying to prevent garbage input
    url_match = re.search(r"https?://\S+", url)
    if not url_match:
        return await event.edit("`[!] Invalid or missing URL.`", time=5)
    url = url_match.group(0)

    try:
        # Import the specific functions rather than the decorated handler
        # to avoid pattern_match context mismatch between userbot and asst
        from assistant.media_dl import show_dl_prompt, dler_process

        if cmd == "yta":
            await dler_process(event, url, "audio")
        elif cmd == "ytv":
            await dler_process(event, url, "video")
        else:
            # .dl — show interactive format selection prompt
            await show_dl_prompt(event, url)

        # Delete the trigger command to keep the chat clean
        await event.delete()
    except Exception as e:
        await event.edit(f"`[Relay Error] {str(e)[:150]}`", time=8)
