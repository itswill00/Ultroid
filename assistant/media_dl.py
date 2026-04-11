# Ultroid Media Downloader Service
# Automatic TikTok, Instagram, and More

import os
import re
import time
import asyncio
from pyUltroid.dB.base import KeyManager
from pyUltroid.fns.extractor import extractor, TIKTOK_RE, INSTAGRAM_RE, TWITTER_RE
from pyUltroid.fns.helper import humanbytes, time_formatter
from pyUltroid.fns.admins import admin_check
from . import asst, asst_cmd, udB, owner_and_sudos, LOGS

# Database Manager for Disabled Chats
# We store 'disabled' chats so the default is 'enabled'
DisabledDL = KeyManager("DISABLED_DL_CHATS", cast=list)

# --------------------------------------------------------------------------
# TOGGLE COMMAND
# --------------------------------------------------------------------------

@asst_cmd(pattern="dlservice( (on|off)|$)", is_group=True)
async def toggle_dl_service(event):
    """Enable or disable auto-downloader in the group."""
    if not await admin_check(event):
        return
    
    cmd = event.pattern_match.group(2)
    chat_id = event.chat_id
    
    if not cmd:
        status = "DISABLED" if DisabledDL.contains(chat_id) else "ENABLED"
        return await event.reply(f"`[DL SERVICE] Current status: {status}`\nUsage: `/dlservice on` or `/dlservice off`")
    
    if cmd == "on":
        if DisabledDL.contains(chat_id):
            DisabledDL.remove(chat_id)
        await event.reply("`[DL SERVICE] Automatic media downloader enabled for this group.`")
    else:
        if not DisabledDL.contains(chat_id):
            DisabledDL.add(chat_id)
        await event.reply("`[DL SERVICE] Automatic media downloader disabled for this group.`")

# --------------------------------------------------------------------------
# AUTOMATIC LISTENER
# --------------------------------------------------------------------------

@asst_cmd(incoming=True, is_group=True)
async def auto_media_downloader(event):
    """Listens for media links and downloads them automatically."""
    if event.text.startswith("/") or DisabledDL.contains(event.chat_id):
        return
    
    text = event.text
    match = TIKTOK_RE.search(text) or INSTAGRAM_RE.search(text) or TWITTER_RE.search(text)
    
    if not match:
        return
    
    url = match.group(0)
    msg = await event.reply("`[DL] Extracting media...`")
    
    start_time = time.time()
    files = await extractor.download(url)
    duration = round(time.time() - start_time, 2)
    
    if not files:
        return await msg.delete() # Silent fail for cleaner UX

    try:
        # Determine Source
        source = "TikTok" if "tiktok" in url else "Instagram" if "instagram" in url else "Twitter/X"
        
        # Fast Upload
        if len(files) == 1:
            file_path = files[0]
            if not os.path.exists(file_path):
                return await msg.delete()
                
            await event.client.send_file(
                event.chat_id,
                file=file_path,
                caption=f"**[ {source} ]**\n\n`Extraction Time: {duration}s`",
                reply_to=event.id
            )
            os.remove(file_path)
        else:
            # Multi-file support (TikTok Slides or IG Carousel)
            valid_files = [f for f in files if os.path.exists(f)]
            if valid_files:
                await event.client.send_file(
                    event.chat_id,
                    file=valid_files,
                    caption=f"**[ {source} (Album) ]**\n\n`Extraction Time: {duration}s`",
                    reply_to=event.id
                )
                for f in valid_files:
                    os.remove(f)
        
        await msg.delete()
    except Exception as e:
        LOGS.error(f"Media Upload Error: {e}")
        await msg.edit(f"`[DL ERROR] Failed to upload media.`")
        # Cleanup
        for f in files:
            if os.path.exists(f): os.remove(f)
