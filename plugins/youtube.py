# Ultroid - UserBot
# Media Downloader Relay (Assistant Proxy)

from pyUltroid import asst
from assistant.media_dl import manual_downloader
from . import ultroid_cmd
import asyncio

@ultroid_cmd(pattern="(dl|yta|ytv)( (.*)|$)")
async def userbot_dl_relay(event):
    """Relays download commands to the Assistant Bot."""
    if not asst:
        return await event.edit("`[!] Assistant Bot is not active. Manual download via Userbot is disabled.`", time=5)
    
    url = event.pattern_match.group(2).strip()
    if not url:
        return await event.edit("`Usage: .dl <link>`", time=5)

    # Relay the work to Assistant
    # We pass the event so manual_downloader can extract chat_id and url
    # assistant will send the choice buttons or start the process.
    try:
        await manual_downloader(event)
        # Delete the trigger command to keep the chat clean
        await event.delete()
    except Exception as e:
        await event.edit(f"`[Relay Error] {str(e)}`", time=5)
