# Ultroid Media Downloader Service
# Automatic TikTok, Instagram, and More

import os
import re
import time
import uuid
import asyncio
from telethon import Button
from pyUltroid import asst, udB, LOGS, _ult_cache
from pyUltroid._misc import owner_and_sudos
from pyUltroid.dB.base import KeyManager
from pyUltroid.fns.extractor import extractor, TIKTOK_RE, INSTAGRAM_RE, TWITTER_RE
from pyUltroid.fns.helper import humanbytes, time_formatter
from pyUltroid.fns.admins import admin_check
from pyUltroid._misc._assistant import asst_cmd, callback

# Database Manager for Disabled Chats
DisabledDL = KeyManager("DISABLED_DL_CHATS", cast=list)

# Initialize Cache for Media Downloads
if "media_dl" not in _ult_cache:
    _ult_cache["media_dl"] = {}

LOGS.info("Loading Universal Media Downloader Service (Interactive Mode)...")

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
    """Listens for media links and sends format selection choice."""
    if not event.text or event.text.startswith("/") or DisabledDL.contains(event.chat_id):
        return
    
    text = event.text
    match = TIKTOK_RE.search(text) or INSTAGRAM_RE.search(text) or TWITTER_RE.search(text)
    
    if not match:
        return
    
    url = match.group(0)
    msg_id = str(uuid.uuid4())[:8] # Unique ID for this specific interaction
    
    # Cache the URL
    _ult_cache["media_dl"][msg_id] = {
        "url": url,
        "sender": event.sender_id,
        "time": time.time()
    }
    
    # Determine Source
    source = "TikTok" if "tiktok" in url else "Instagram" if "instagram" in url else "Twitter/X"
    
    # Selection Card
    buttons = [
        [
            Button.inline("🎬 Video", data=f"get_dl|video|{msg_id}"),
            Button.inline("🎵 Audio", data=f"get_dl|audio|{msg_id}")
        ],
        [Button.inline("🗑️ Dismiss", data="close_dl")]
    ]
    
    await event.reply(
        f"**[ {source} Detected ]**\nHow would you like to download this media?",
        buttons=buttons
    )

# --------------------------------------------------------------------------
# CALLBACK HANDLERS
# --------------------------------------------------------------------------

@callback(re.compile("get_dl\\|(video|audio)\\|(.*)"))
async def process_media_selection(event):
    """Handles format selection for media downloads."""
    fmt = event.pattern_match.group(1).decode("utf-8")
    msg_id = event.pattern_match.group(2).decode("utf-8")
    
    data = _ult_cache["media_dl"].get(msg_id)
    if not data:
        return await event.answer("Download prompt expired or invalid.", alert=True)
    
    url = data["url"]
    await event.edit(f"`[DL] Preparing {fmt.upper()}... please wait.`")
    
    try:
        start_time = time.time()
        # Extract metadata (once more for fresh info)
        info = await extractor.extract(url)
        if not info:
             return await event.edit("`[DL ERROR] Failed to fetch metadata.`")

        # Start download with selected format
        files = await extractor.download(url, format_type=fmt)
        duration = round(time.time() - start_time, 2)
        
        if not files:
            return await event.edit("`[DL ERROR] Extraction failed.`")

        # Determine Source and Metadata
        source = "TikTok" if "tiktok" in url else "Instagram" if "instagram" in url else "Twitter/X"
        uploader = info.get("uploader") or info.get("uploader_id") or "Unknown"
        uploader_url = info.get("uploader_url") or url
        title = info.get("title") or info.get("description") or ""
        if len(title) > 150: title = title[:147] + "..."
        
        # Delivery
        caption = f"**Uploaded by [{uploader}]({uploader_url})**\n\n"
        if title:
            caption += f"`{title}`\n\n"
        caption += f"**[ {source} | {fmt.upper()} ]** • `{duration}s`"
        
        # Final delivery
        valid_files = [f for f in files if os.path.exists(f)]
        if not valid_files:
            return await event.edit("`[DL ERROR] File download failed.`")

        # Use send_file with EXPLICIT message_id to avoid 64-bit struct error
        await event.client.send_file(
            event.chat_id,
            file=valid_files if len(valid_files) > 1 else valid_files[0],
            caption=caption,
            reply_to=event.message_id,
            buttons=[[Button.inline("🗑️ Close", data="close_dl")]]
        )
        
        # Cleanup
        for f in valid_files:
            if os.path.exists(f): os.remove(f)
        await event.delete()
        
        # Remove from cache after success
        _ult_cache["media_dl"].pop(msg_id, None)

    except Exception as e:
        LOGS.error(f"Media Selection Error: {e}")
        await event.edit(f"`[DL ERROR] {str(e)[:100]}`")

@callback(re.compile("close_dl"))
async def close_media(event):
    await event.delete()
