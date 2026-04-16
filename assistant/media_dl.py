"""
★ Universal Media Downloader ★

Provides an interactive GUI format selection for TikTok, Instagram, Twitter, and YouTube links.
Includes automatic chat listener functionality for completely seamless background downloads, 
as well as manual `/dl`, `/yta`, and `/ytv` command triggers.
"""

# Ultroid Media Downloader Service
# Automatic TikTok, Instagram, and More

import os
import re
import time
import uuid
import asyncio
import shutil
try:
    from yt_dlp.utils import DownloadCancelled
except ImportError:
    class DownloadCancelled(Exception): pass
from telethon import Button
from pyUltroid import asst, udB, LOGS, _ult_cache, ultroid_bot
from pyUltroid._misc import owner_and_sudos
from pyUltroid.dB.base import KeyManager
from pyUltroid.fns.extractor import extractor, TIKTOK_RE, INSTAGRAM_RE, TWITTER_RE, ADULT_RE
from pyUltroid.fns.helper import humanbytes, time_formatter, progress, uploadable
from pyUltroid.fns.admins import admin_check
from pyUltroid._misc._assistant import asst_cmd, callback

# Database Manager for Disabled Chats
DisabledDL = KeyManager("DISABLED_DL_CHATS", cast=list)

# Initialize Cache for Media Downloads
if "media_dl" not in _ult_cache:
    _ult_cache["media_dl"] = {}

# Tracker for Cancelled Jobs
if "cancel_jobs" not in _ult_cache:
    _ult_cache["cancel_jobs"] = set()

# Tracker for Job Ownership (UID)
if "job_owners" not in _ult_cache:
    _ult_cache["job_owners"] = {}

LOGS.info("Loading Universal Media Downloader Service (Interactive Mode)...")

# --------------------------------------------------------------------------
# HELPERS
# --------------------------------------------------------------------------

async def show_dl_prompt(event, url):
    """Sends format selection choice."""
    msg_id = str(uuid.uuid4())[:8]
    _ult_cache["media_dl"][msg_id] = {
        "url": url,
        "sender": event.sender_id,
        "time": time.time()
    }
    
    source = "TikTok" if "tiktok" in url else "Instagram" if "instagram" in url else "Twitter/X" if ("twitter" in url or "/x.com" in url) else "🔞 NSFW Media" if re.search(r"pornhub|xvideos|xhamster|xnxx|spankbang|eporner", url) else "🌐 Universal Media"
    
    if "NSFW" in source or "Universal" in source:
        buttons = [
            [
                Button.inline("🎬 1080p", data=f"get_dl|1080|{msg_id}"),
                Button.inline("🎬 720p", data=f"get_dl|720|{msg_id}"),
                Button.inline("🎬 480p", data=f"get_dl|480|{msg_id}")
            ],
            [Button.inline("🎵 Audio", data=f"get_dl|audio|{msg_id}"), Button.inline("🗑️ Dismiss", data="close_dl")]
        ]
    else:
        buttons = [
            [
                Button.inline("🎬 Video", data=f"get_dl|video|{msg_id}"),
                Button.inline("🎵 Audio", data=f"get_dl|audio|{msg_id}")
            ],
            [Button.inline("🗑️ Dismiss", data="close_dl")]
        ]
    
    await asst.send_message(
        event.chat_id,
        f"**[ {source} | Downloader ]**\nSelect download format:",
        buttons=buttons,
        reply_to=event.id
    )

async def dler_process(event, url, fmt):
    """Core download and delivery logic."""
    start_time = time.time()
    # If the event is a callback, edit it. If it's a message, reply/send.
    is_callback = hasattr(event, "answer")
    
    status_msg = await asst.send_message(event.chat_id, f"`[DL] Processing {fmt.upper()}...`")
    
    valid_files = []
    job_id = str(uuid.uuid4())[:8]
    _ult_cache["job_owners"][job_id] = event.sender_id
    loop = asyncio.get_running_loop()
    last_update = [0]
    cancel_btn = [Button.inline("❌ Cancel", data=f"cancel_dl|{job_id}")]

    def dl_progress_hook(d):
        # Immediate Termination Check
        if job_id in _ult_cache["cancel_jobs"]:
            raise DownloadCancelled("Download aborted by user.")

        if d.get('status') in ['downloading', 'finished']:
            now = time.time()
            if now - last_update[0] > 3 or d.get('status') == 'finished':
                last_update[0] = now
                current = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                if total:
                    try:
                        asyncio.run_coroutine_threadsafe(
                            progress(current, total, status_msg, start_time, f"📥 Downloading {fmt.upper()}...", buttons=cancel_btn),
                            loop
                        )
                    except:
                        pass

    try:
        info = await extractor.extract(url)
        if not info or "error" in info:
            err = info.get("error", "Unknown Extraction Error.") if info else "Failed to fetch metadata."
            return await status_msg.edit(f"`[DL ERROR] {err}`")

        files = await extractor.download(url, format_type=fmt, job_id=job_id, progress_callback=dl_progress_hook)
        duration = round(time.time() - start_time, 2)
        
        if not files:
            return await status_msg.edit("`[DL ERROR] Extraction failed.`")

        valid_files = [f for f in files if os.path.exists(f)]
        if not valid_files:
            return await status_msg.edit("`[DL ERROR] File download failed.`")

        total_size = sum(os.path.getsize(f) for f in valid_files)
        if total_size > 2 * 1024 * 1024 * 1024:
            return await status_msg.edit(f"`[DL ERROR] File too large ({humanbytes(total_size)}).`")
        
        # Hybrid Payload Router 
        source = "TikTok" if "tiktok" in url else "Instagram" if "instagram" in url else "Twitter/X" if ("twitter" in url or "/x.com" in url) else "🔞 NSFW Media" if re.search(r"pornhub|xvideos|xhamster|xnxx|spankbang|eporner", url) else "🌐 Universal Media"
        uploader = info.get("uploader") or info.get("uploader_id") or "Unknown"
        uploader_url = info.get("uploader_url") or url
        title = info.get("title") or info.get("description") or ""
        if len(title) > 150: title = title[:147] + "..."

        if total_size > 50 * 1024 * 1024:
            sender_client = ultroid_bot
        else:
            sender_client = asst

        caption = (
            f"**[ {source} | {fmt.upper()} ]**\n"
            f"---"
            f"\n👤 **Uploader:** [{uploader}]({uploader_url})"
            f"\n📄 **Title:** `{title}`"
            f"\n⏱️ **Duration:** `{duration}s`"
            f"\n📦 **Size:** `{humanbytes(total_size)}`"
        )
        
        # Define Upload Progress Hook
        async def up_progress_hook(current, total, header=None):
            # Also check cancellation during upload phase
            if job_id in _ult_cache["cancel_jobs"]:
                # For uploads we can just stop the task
                raise Exception("Upload aborted by user.")
            
            header = header or f"📤 Uploading {fmt.upper()} to Telegram..."
            await progress(current, total, status_msg, start_time, header, buttons=cancel_btn)

        file_to_send = valid_files if len(valid_files) > 1 else valid_files[0]
        
        # Hybrid Payload Router 
        # For files > 50MB, the Userbot MUST be the sender (Bot API limit)
        if total_size > 50 * 1024 * 1024:
            sender_client = ultroid_bot
            if isinstance(file_to_send, str):
                await status_msg.edit(f"`[🚀 Turbo Relay] Size: {humanbytes(total_size)}. Initializing High-Speed Parallel Upload...`")
                with open(file_to_send, 'rb') as f:
                    file_to_send = await uploadable(ultroid_bot, f, os.path.basename(file_to_send), 
                                                progress_callback=lambda c, t: asyncio.run_coroutine_threadsafe(up_progress_hook(c, t, "🚀 Turbo-Relay Uploading..."), loop))
        else:
            sender_client = asst

        await sender_client.send_file(
            event.chat_id,
            file=file_to_send,
            caption=caption,
            reply_to=event.message_id if is_callback else event.id,
            progress_callback=up_progress_hook if total_size <= 50 * 1024 * 1024 else None,
            buttons=[[Button.inline("🗑️ Close", data="close_dl")]]
        )
        await status_msg.delete()
    except DownloadCancelled:
        await status_msg.edit("`[DL] Task aborted by user. Cleanup complete.`")
    except Exception as e:
        if "aborted" in str(e):
            await status_msg.edit("`[DL] Task aborted by user.`")
        else:
            LOGS.error(f"Downloader Error: {e}")
            await status_msg.edit(f"`[DL ERROR] {str(e)[:100]}`")
    finally:
        _ult_cache["cancel_jobs"].discard(job_id)
        _ult_cache["job_owners"].pop(job_id, None)
        shutil.rmtree(f"downloads/{job_id}", ignore_errors=True)

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
# MANUAL COMMANDS
# --------------------------------------------------------------------------

@asst_cmd(pattern="(dl|yta|ytv)( (.*)|$)")
async def manual_downloader(event):
    """Explicitly trigger downloader via command."""
    cmd = event.pattern_match.group(1)
    url = event.pattern_match.group(2).strip()
    
    if not url:
        return await event.reply(f"`Usage: /{cmd} <link>`")
    
    # Clean URL
    match = re.search(r"https?://\S+", url)
    if not match:
        return await event.reply("`Invalid or missing URL.`")
    url = match.group(0)
    
    if cmd == "yta":
        await dler_process(event, url, "audio")
    elif cmd == "ytv":
        await dler_process(event, url, "video")
    else:
        await show_dl_prompt(event, url)

# --------------------------------------------------------------------------
# AUTOMATIC LISTENER
# --------------------------------------------------------------------------

@asst_cmd(incoming=True, func=lambda e: e.is_group)
async def auto_media_downloader(event):
    """Listens for media links in groups."""
    # Self-Ignore Filter (Anti-Loop)
    asst_me = await asst.get_me()
    userbot_me = await ultroid_bot.get_me()
    if event.sender_id in [asst_me.id, userbot_me.id]:
        return

    if not event.text or event.text.startswith("/") or DisabledDL.contains(event.chat_id):
        return
    
    text = event.text
    match = TIKTOK_RE.search(text) or INSTAGRAM_RE.search(text) or TWITTER_RE.search(text) or ADULT_RE.search(text)
    
    if match:
        await show_dl_prompt(event, match.group(0))

# --------------------------------------------------------------------------
# CALLBACK HANDLERS
# --------------------------------------------------------------------------

@callback(re.compile(b"get_dl\\|(1080|720|480|video|audio)\\|(.*)"))
async def process_media_selection(event):
    """Handles format selection for media downloads."""
    fmt = event.pattern_match.group(1).decode("utf-8")
    msg_id = event.pattern_match.group(2).decode("utf-8")
    
    data = _ult_cache["media_dl"].get(msg_id)
    if not data:
        return await event.answer("Download prompt expired.", alert=True)
    
    url = data["url"]
    # Deleting picker immediately for UI cleanup
    await event.delete()
    await dler_process(event, url, fmt)
    _ult_cache["media_dl"].pop(msg_id, None)

@callback(re.compile("close_dl"))
async def close_media(event):
    await event.delete()

@callback(re.compile(b"cancel_dl\\|(.*)"))
async def process_media_cancel(event):
    """Signals a background download job to terminate with Auth Check."""
    job_id = event.pattern_match.group(1).decode("utf-8")
    
    # Authorization Check
    owner_id = _ult_cache["job_owners"].get(job_id)
    is_admin = await admin_check(event, silent=True)
    is_sudo = event.sender_id in (owner_and_sudos())
    
    if owner_id and event.sender_id != owner_id and not (is_admin or is_sudo):
        return await event.answer("❌ Access Denied: Only the requester or admins can cancel this task.", alert=True)

    _ult_cache["cancel_jobs"].add(job_id)
    await event.answer("❌ Cancellation signal sent. Stopping task...", alert=True)
    await event.edit("`[DL] Aborting task... Clearing temporary files.`")
