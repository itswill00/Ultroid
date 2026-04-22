# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/TeamUltroid/pyUltroid/blob/main/LICENSE>.

import os
import re
import time

try:
    import httpx
    _old_post = httpx.post
    def _new_post(*args, **kwargs):
        kwargs.pop("proxies", None)
        return _old_post(*args, **kwargs)
    httpx.post = _new_post

    _old_Client_post = httpx.Client.post
    def _new_Client_post(self, *args, **kwargs):
        kwargs.pop("proxies", None)
        return _old_Client_post(self, *args, **kwargs)
    httpx.Client.post = _new_Client_post
except Exception:
    pass

from telethon import Button

try:
    from youtubesearchpython import Playlist, VideosSearch
except ImportError:
    Playlist, VideosSearch = None, None


from .. import LOGS
from .extractor import extractor
from .helper import humanbytes, run_async, time_formatter
from .tools import set_attributes


async def ytdl_progress(k, start_time, event):
    if k["status"] == "error":
        return await event.edit("error")
    while k["status"] == "downloading":
        text = (
            f"`Downloading: {k['filename']}\n"
            + f"Total Size: {humanbytes(k['total_bytes'])}\n"
            + f"Downloaded: {humanbytes(k['downloaded_bytes'])}\n"
            + f"Speed: {humanbytes(k['speed'])}/s\n"
            + f"ETA: {time_formatter(k['eta']*1000)}`"
        )
        if round((time.time() - start_time) % 10.0) == 0:
            try:
                await event.edit(text)
            except Exception as ex:
                LOGS.error(f"ytdl_progress: {ex}")


def get_yt_link(query):
    search = VideosSearch(query, limit=1).result()
    try:
        return search["result"][0]["link"]
    except IndexError:
        return


async def download_yt(event, link, ytd):
    reply_to = event.reply_to_msg_id or event
    info = await dler(event, link, ytd, download=True)
    if not info:
        return

    local_files = info.get("local_files") or []
    if not local_files:
        return await event.edit("`[Error] No files downloaded.`")

    total = len(local_files)
    title = info.get("title") or "Downloaded Media"

    # Send files
    for num, file_path in enumerate(local_files, start=1):
        if not os.path.exists(file_path):
            continue

        # Prepare attributes (for video/audio meta)
        attributes = await set_attributes(file_path)

        # Upload
        res, _ = await event.client.fast_uploader(
            file_path, show_progress=True, event=event, to_delete=True
        )

        # Caption
        from_ = info.get("extractor", "Universal")
        caption = f"**{title}**"
        if total > 1:
            caption = f"`[{num}/{total}]` " + caption
        caption += f"\n\n`from {from_}`"

        # Send
        await event.client.send_file(
            event.chat_id,
            file=res,
            caption=caption,
            attributes=attributes,
            supports_streaming=True,
            reply_to=reply_to,
        )

    try:
        await event.delete()
    except Exception:
        pass


# ---------------YouTube Downloader Inline---------------
# @New-Dev0 @buddhhu @1danish-00


def get_formats(type, id, data):
    if type == "audio":
        audio = []
        for _quality in ["64", "128", "256", "320"]:
            _audio = {}
            _audio.update(
                {
                    "ytid": id,
                    "type": "audio",
                    "id": _quality,
                    "quality": _quality + "KBPS",
                }
            )
            audio.append(_audio)
        return audio
    if type == "video":
        video = []
        size = 0
        for vid in data["formats"]:
            if vid["format_id"] == "251":
                size += vid["filesize"] if vid.get("filesize") else 0
            if vid["vcodec"] != "none":
                _id = int(vid["format_id"])
                _quality = str(vid["width"]) + "×" + str(vid["height"])
                _size = size + (vid["filesize"] if vid.get("filesize") else 0)
                _ext = "mkv" if vid["ext"] == "webm" else "mp4"
                if _size < 2147483648:  # Telegram's Limit of 2GB
                    _video = {}
                    _video.update(
                        {
                            "ytid": id,
                            "type": "video",
                            "id": str(_id) + "+251",
                            "quality": _quality,
                            "size": _size,
                            "ext": _ext,
                        }
                    )
                    video.append(_video)
        return video
    return []


def get_buttons(listt):
    id = listt[0]["ytid"]
    butts = [
        Button.inline(
            text=f"[{x['quality']}"
            + (f" {humanbytes(x['size'])}]" if x.get("size") else "]"),
            data=f"ytdownload:{x['type']}:{x['id']}:{x['ytid']}"
            + (f":{x['ext']}" if x.get("ext") else ""),
        )
        for x in listt
    ]
    buttons = list(zip(butts[::2], butts[1::2], strict=False))
    if len(butts) % 2 == 1:
        buttons.append((butts[-1],))
    buttons.append([Button.inline("« Back", f"ytdl_back:{id}")])
    return buttons


async def dler(event, url, opts: dict = None, download=False):
    """Unified downloader bridge for Userbot plugins."""
    if opts is None:
        opts = {}
    await event.edit("`[DL] Processing Request...`")
    fmt = "video"
    if opts.get("format") == "bestaudio":
        fmt = "audio"
    try:
        if download:
            files = await extractor.download(url, format_type=fmt)
            if not files: return None
            info = await extractor.extract(url)
            if isinstance(files, list):
                info["local_files"] = files
                info["id"] = info.get("id") or "downloaded_media"
            return info
        else:
            return await extractor.extract(url)
    except Exception as e:
        await event.edit(f"`[Error] {str(e)[:100]}`")
        return None


@run_async
def get_videos_link(url):
    to_return = []
    regex = re.search(r"\?list=([(\w+)\-]*)", url)
    if not regex:
        return to_return
    playlist_id = regex.group(1)
    videos = Playlist(playlist_id)
    for vid in videos.videos:
        link = re.search(r"\?v=([(\w+)\-]*)", vid["link"]).group(1)
        to_return.append(f"https://youtube.com/watch?v={link}")
    return to_return
