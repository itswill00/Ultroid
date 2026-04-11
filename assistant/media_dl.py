# Ultroid Media Downloader Service
# Automatic TikTok, Instagram, and More

import os
import re
import time
import asyncio
from telethon import Button
from pyUltroid import asst, udB, LOGS
from pyUltroid._misc import owner_and_sudos
from pyUltroid.dB.base import KeyManager
from pyUltroid.fns.extractor import extractor, TIKTOK_RE, INSTAGRAM_RE, TWITTER_RE
from pyUltroid.fns.helper import humanbytes, time_formatter
from pyUltroid.fns.admins import admin_check
from pyUltroid._misc._assistant import asst_cmd

# Database Manager for Disabled Chats
DisabledDL = KeyManager("DISABLED_DL_CHATS", cast=list)

LOGS.info("Loading Universal Media Downloader Service...")

# --------------------------------------------------------------------------
# DEBUG COMMAND
# --------------------------------------------------------------------------

@asst_cmd(pattern="dlping$")
async def dl_ping(event):
    """Test if the downloader service is alive."""
    await event.reply("`[DL SERVICE] I am alive and listening!`")

# --------------------------------------------------------------------------
# TOGGLE COMMAND
# --------------------------------------------------------------------------

@asst_cmd(pattern="dlservice( (on|off)|$)", func=lambda e: e.is_group)
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

@asst_cmd(incoming=True, func=lambda e: e.is_group)
async def auto_media_downloader(event):
    """Listens for media links and downloads them automatically."""
    # Ignore if service is disabled or it's a command
    if not event.text or event.text.startswith("/") or DisabledDL.contains(event.chat_id):
        return
    
    text = event.text
    match = TIKTOK_RE.search(text) or INSTAGRAM_RE.search(text) or TWITTER_RE.search(text)
    
    if not match:
        return
    
    url = match.group(0)
    msg = await event.reply("`[DL] Processing media...`")
    
    try:
        start_time = time.time()
        # Extract metadata first
        info = await extractor.extract(url)
        if not info:
             return await msg.edit("`[DL ERROR] Failed to fetch metadata.`")

        # Download media
        files = await extractor.download(url)
        duration = round(time.time() - start_time, 2)
        
        if not files:
            return await msg.delete()

        # Determine Source and Metadata
        source = "TikTok" if "tiktok" in url else "Instagram" if "instagram" in url else "Twitter/X"
        uploader = info.get("uploader") or info.get("uploader_id") or "Unknown"
        uploader_url = info.get("uploader_url") or url
        title = info.get("title") or info.get("description") or ""
        # Clean title (limit length)
        if len(title) > 150: title = title[:147] + "..."
        
        # Build Caption (Minimalist & Professional)
        caption = f"**Uploaded by [{uploader}]({uploader_url})**\n\n"
        if title:
            caption += f"`{title}`\n\n"
        caption += f"**[ {source} ]** • `{duration}s`"
        
        # Buttons
        buttons = [
            [
                Button.url("View Original", url=url),
                Button.inline("Share", data="share_dl")
            ],
            [Button.inline("🗑️ Close", data="close_dl")]
        ]

        # Filter existing files
        valid_files = [f for f in files if os.path.exists(f)]
        if not valid_files:
            return await msg.edit("`[DL ERROR] File download failed.`")

        # Upload
        await event.client.send_file(
            event.chat_id,
            file=valid_files if len(valid_files) > 1 else valid_files[0],
            caption=caption,
            buttons=buttons,
            reply_to=event.id
        )
        
        # Cleanup
        for f in valid_files:
            if os.path.exists(f): os.remove(f)
        await msg.delete()

    except Exception as e:
        LOGS.error(f"Media Downloader Error: {e}")
        await msg.edit(f"`[DL ERROR] {str(e)[:100]}`")

# --------------------------------------------------------------------------
# CALLBACKS
# --------------------------------------------------------------------------

@callback(re.compile("close_dl"))
async def close_media(event):
    await event.delete()

@callback(re.compile("share_dl"))
async def share_media(event):
    await event.answer("Feature coming soon: Sharing to other chats.", alert=True)
