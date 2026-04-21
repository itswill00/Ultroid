# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

from . import get_help

__doc__ = get_help("gdrive")

"""
✘ Commands Available

• `{i}gdul <reply/file name>`
    Reply to file to upload on Google Drive.
    Add file name to upload on Google Drive.

• `{i}gdown <file id/link> | <filename>`
    Download from Gdrive link or file id.

• `{i}gdsearch <file name>`
    Search file name on Google Drive and get link.

• `{i}gdlist`
    List all GDrive files.

• `{i}gdfolder`
    Link to your Google Drive Folder.
    If added then all files will be uploaded in this folder.
"""

import asyncio
import os
import time

from pyUltroid.fns.gDrive import GDriveManager
from pyUltroid.fns.helper import humanbytes, time_formatter

from . import ULTConfig, asst, eod, eor, get_string, ultroid_cmd


@ultroid_cmd(
    pattern="gdown( (.*)|$)",
    fullsudo=True,
)
async def gdown(event):
    GDrive = GDriveManager()
    match = event.pattern_match.group(1).strip()
    if not match:
        return await eod(event, "`Give file id or Gdrive link to download from!`")

    filename = None
    if " | " in match:
        parts = match.split(" | ")
        match = parts[0].strip()
        filename = parts[1].strip()

    eve = await event.eor(get_string("com_1"))
    _start = time.time()

    status, response = await GDrive._download_file(eve, match, filename)
    if not status:
        return await eve.edit(f"**Error:** `{response}`")

    await eve.edit(
        f"**✦ Downloaded Successfully**\n"
        f"**File:** `{response}`\n"
        f"**Time taken:** `{time_formatter((time.time() - _start)*1000)}`"
    )


@ultroid_cmd(
    pattern="gdlist$",
    fullsudo=True,
)
async def files(event):
    GDrive = GDriveManager()
    if not os.path.exists(GDrive.token_file):
        return await event.eor(get_string("gdrive_6").format(asst.me.username))

    eve = await event.eor(get_string("com_1"))
    files_dict = await GDrive._list_files()

    if not files_dict:
        return await eve.edit("`No files found in G-Drive.`")

    msg = f"**Total {len(files_dict)} files found in G-Drive:**\n\n"
    for link, name in files_dict.items():
        msg += f"• [{name}]({link})\n"

    if len(msg) < 4096:
        await eve.edit(msg, link_preview=False)
    else:
        file_path = "drive-files.txt"
        with open(file_path, "w", encoding='utf-8') as f:
            f.write(msg.replace("• [", "File: ").replace("](", "\nLink: ").replace(")\n", "\n\n"))

        await event.client.send_file(
            event.chat_id,
            file_path,
            caption="`GDrive File List`",
            thumb=ULTConfig.thumb,
            reply_to=event,
        )
        os.remove(file_path)
        await eve.delete()


@ultroid_cmd(
    pattern="gdul( (.*)|$)",
    fullsudo=True,
)
async def _(event):
    GDrive = GDriveManager()
    if not os.path.exists(GDrive.token_file):
        return await eod(event, get_string("gdrive_6").format(asst.me.username))

    input_file = event.pattern_match.group(1).strip()
    reply = await event.get_reply_message()

    if not input_file and not reply:
        return await eod(event, "`Reply to a file or provide a local path.`")

    mone = await event.eor(get_string("com_1"))

    if reply and reply.media:
        location = "resources/downloads"
        if not os.path.isdir(location):
            os.makedirs(location)

        if reply.photo:
            filename = await reply.download_media(location)
        else:
            filename = reply.file.name or str(round(time.time()))
            filename = os.path.join(location, filename)
            try:
                # Using fast_downloader for efficiency
                file_obj, _ = await event.client.fast_downloader(
                    file=reply.media.document if hasattr(reply.media, 'document') else reply.media,
                    filename=filename,
                    show_progress=True,
                    event=mone,
                    message="`✦ Downloading to server...`",
                )
                filename = filename # fast_downloader might update it if it's different
            except Exception as e:
                return await eor(mone, f"**Download Error:** `{e}`", time=10)
        await mone.edit(f"`✦ Downloaded to server: ``{os.path.basename(filename)}``\nUploading to GDrive...`")
    else:
        filename = input_file
        if not os.path.exists(filename):
            return await eod(mone, "`File/Folder not found on server.`", time=5)

    try:
        if os.path.isdir(filename):
            files_list = os.listdir(filename)
            if not files_list:
                return await eod(mone, "`Directory is empty.`")

            folder_id = await GDrive.create_directory(os.path.basename(filename))
            count = 0
            for f in sorted(files_list):
                file_path = os.path.join(filename, f)
                if os.path.isfile(file_path):
                    try:
                        await GDrive._upload_file(mone, path=file_path, folder_id=folder_id)
                        count += 1
                    except Exception as e:
                        return await mone.edit(f"**Upload Error on {f}:** `{e}`")

            await mone.edit(
                f"**✦ Folder Uploaded Successfully**\n"
                f"**Folder:** [{os.path.basename(filename)}](https://drive.google.com/folderview?id={folder_id})\n"
                f"**Total Files:** `{count}`"
            )
        else:
            g_drive_link = await GDrive._upload_file(mone, filename)
            await mone.edit(
                get_string("gdrive_7").format(os.path.basename(filename), g_drive_link),
                link_preview=False
            )
    except Exception as e:
        await mone.edit(f"**Error during GDrive operation:** `{e}`")


@ultroid_cmd(
    pattern="gdsearch( (.*)|$)",
    fullsudo=True,
)
async def _(event):
    GDrive = GDriveManager()
    if not os.path.exists(GDrive.token_file):
        return await event.eor(get_string("gdrive_6").format(asst.me.username))

    input_str = event.pattern_match.group(1).strip()
    if not input_str:
        return await event.eor("`Give a filename to search...`")

    eve = await event.eor(f"`✦ Searching for '{input_str}' in G-Drive...`")
    files_dict = await GDrive.search(input_str)

    if not files_dict:
        return await eve.edit(f"`No files found matching '{input_str}'`")

    msg = f"**Found {len(files_dict)} results for '{input_str}':**\n\n"
    for link, name in files_dict.items():
        msg += f"• [{name}]({link})\n"

    if len(msg) < 4096:
        await eve.edit(msg, link_preview=False)
    else:
        file_path = f"{input_str}_search.txt"
        with open(file_path, "w", encoding='utf-8') as f:
            f.write(msg.replace("• [", "File: ").replace("](", "\nLink: ").replace(")\n", "\n\n"))

        await event.client.send_file(
            event.chat_id,
            file_path,
            caption=f"`Search results for {input_str}`",
            thumb=ULTConfig.thumb,
            reply_to=event,
        )
        os.remove(file_path)
        await eve.delete()


@ultroid_cmd(
    pattern="gdfolder$",
    fullsudo=True,
)
async def _(event):
    GDrive = GDriveManager()
    if not os.path.exists(GDrive.token_file):
        return await event.eor(get_string("gdrive_6").format(asst.me.username))

    if GDrive.folder_id:
        await event.eor(
            f"**Your G-Drive Folder Link:**\n"
            f"{GDrive._create_folder_link(GDrive.folder_id)}"
        )
    else:
        await eod(event, "`GDRIVE_FOLDER_ID not set. Please set it in Assistant Bot settings.`")

@ultroid_cmd(
    pattern="gdstats$",
    fullsudo=True,
)
async def gdrive_stats(event):
    GDrive = GDriveManager()
    if not os.path.exists(GDrive.token_file):
        return await event.eor(get_string("gdrive_6").format(asst.me.username))

    eve = await event.eor("`✦ Fetching G-Drive Storage Stats...`")
    data = await asyncio.to_thread(GDrive.get_storage_usage)

    if not data:
        return await eve.edit(
            "`Failed to fetch storage stats. Make sure you are authorized.`"
        )

    total = data["total"]
    used = data["used"]
    free = data["free"]
    pct = data["percentage"]

    msg = "**📊 Google Drive Storage Stats**\n"
    msg += "---"
    msg += f"\n**Total Capacity:** `{total}`"
    msg += f"\n**Used Space:** `{used}`"
    msg += f"\n**Remaining:** `{free}`\n\n"

    if pct is not None:
        # Generate a nice progress bar
        filled = int(pct // 10)
        bar = "█" * filled + "░" * (10 - filled)
        msg += f"**Usage:** `[{bar}] {pct}%`"
    else:
        msg += "**Usage:** `Unlimited`"

    await eve.edit(msg)


@ultroid_cmd(
    pattern="gdleech( (.*)|$)",
    fullsudo=True,
)
async def gdrive_leech(event):
    GDrive = GDriveManager()
    if not os.path.exists(GDrive.token_file):
        return await event.eor(get_string("gdrive_6").format(asst.me.username))

    match = event.pattern_match.group(1).strip()
    if not match:
        return await event.eor("`Give GDrive file link or ID to leech!`")

    eve = await event.eor("`✦ Analyzing G-Drive link...`")
    info = await GDrive.get_file_info(match)

    if not info:
        return await eve.edit(
            "`Failed to fetch file info. Make sure the link is correct and accessible.`"
        )

    filename = info.get("name")
    size = int(info.get("size", 0))

    # Telegram limit: 2GB
    if size > 2 * 1024 * 1024 * 1024:
        return await eve.edit(
            f"**Error:** File size is too large (`{humanbytes(size)}`). Telegram limit is 2GB."
        )

    await eve.edit(
        f"**✦ Leeching to Telegram**\n**File:** `{filename}`\n**Size:** `{humanbytes(size)}`\n\n`✦ Downloading to VPS...`"
    )

    _start = time.time()
    status, response = await GDrive._download_file(eve, info["id"], filename)
    if not status:
        return await eve.edit(f"**Download Error:** `{response}`")

    await eve.edit("`✦ Uploading to Telegram...`")

    try:
        from pyUltroid.fns.helper import uploader

        await uploader(
            file=response,
            name=os.path.basename(response),
            taime=_start,
            event=event,
            msg=eve,
        )
    except Exception as e:
        await eve.edit(f"**Upload Error:** `{e}`")
    finally:
        if os.path.exists(response):
            os.remove(response)
