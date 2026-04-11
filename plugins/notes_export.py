# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.
"""
✘ Commands Available -

• `{i}exportnotes`
    Export semua saved notes ke file .txt dan kirim ke Saved Messages.

• `{i}exportmsg <jumlah>`
    Ekspor N pesan terakhir dari chat saat ini ke file .txt.

• `{i}exportmd`
    Export semua notes ke format Markdown (.md).
"""

import os
from datetime import datetime

from . import udB, ultroid_cmd, LOGS

help_exportnotes = __doc__


@ultroid_cmd(pattern="exportnotes$")
async def export_notes(e):
    """Export all saved notes to a text file."""
    xx = await e.eor("`[EXPORT] Mengambil semua notes...`")
    try:
        from pyUltroid.dB.notes_db import get_all_notes
        notes = get_all_notes(e.chat_id)
    except Exception:
        notes = None

    if not notes:
        return await xx.edit("`[EXPORT] Tidak ada notes yang ditemukan di chat ini.`")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"notes_export_{ts}.txt"
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# Notes Export — {datetime.now().strftime('%d %b %Y %H:%M:%S')}\n")
            f.write(f"# Chat: {e.chat_id}\n")
            f.write("─" * 50 + "\n\n")
            for i, (keyword, content) in enumerate(notes.items(), 1):
                f.write(f"[{i}] Keyword: {keyword}\n")
                f.write(f"Content:\n{content}\n")
                f.write("─" * 30 + "\n\n")

        await e.client.send_file(
            e.chat_id,
            filename,
            caption=f"`[EXPORT] {len(notes)} notes berhasil diekspor.`",
            reply_to=e.id,
        )
        await xx.delete()
    except Exception as err:
        LOGS.exception(err)
        await xx.edit(f"`[EXPORT] Gagal: {err}`")
    finally:
        if os.path.exists(filename):
            os.remove(filename)


@ultroid_cmd(pattern="exportmsg( (.*)|$)")
async def export_messages(e):
    """Export recent messages from current chat to a text file."""
    match = e.pattern_match.group(1).strip()
    try:
        limit = int(match) if match.isdigit() else 50
        limit = min(limit, 500)  # cap at 500
    except Exception:
        limit = 50

    xx = await e.eor(f"`[EXPORT] Mengambil {limit} pesan terakhir...`")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"messages_export_{ts}.txt"
    count = 0
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# Messages Export — {datetime.now().strftime('%d %b %Y %H:%M:%S')}\n")
            f.write(f"# Chat: {e.chat_id} | Limit: {limit}\n")
            f.write("─" * 50 + "\n\n")
            async for msg in e.client.iter_messages(e.chat_id, limit=limit):
                if not msg.text:
                    continue
                sender = getattr(msg.sender, "first_name", "Unknown") or "Unknown"
                ts_msg = msg.date.strftime("%d/%m/%Y %H:%M")
                f.write(f"[{ts_msg}] {sender}:\n{msg.text}\n\n")
                count += 1

        if count == 0:
            await xx.edit("`[EXPORT] Tidak ada pesan teks yang bisa diekspor.`")
        else:
            await e.client.send_file(
                e.chat_id,
                filename,
                caption=f"`[EXPORT] {count} pesan berhasil diekspor.`",
                reply_to=e.id,
            )
            await xx.delete()
    except Exception as err:
        LOGS.exception(err)
        await xx.edit(f"`[EXPORT] Gagal: {err}`")
    finally:
        if os.path.exists(filename):
            os.remove(filename)


@ultroid_cmd(pattern="exportmd$")
async def export_md(e):
    """Export all notes from database in Markdown format."""
    xx = await e.eor("`[EXPORT] Menyiapkan ekspor Markdown...`")
    try:
        from pyUltroid.dB.notes_db import get_all_notes
        notes = get_all_notes(e.chat_id)
    except Exception:
        notes = None

    if not notes:
        return await xx.edit("`[EXPORT] Tidak ada notes yang ditemukan.`")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"notes_export_{ts}.md"
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# Notes Export\n\n")
            f.write(f"> Generated: {datetime.now().strftime('%d %b %Y %H:%M:%S')}\n\n")
            f.write("---\n\n")
            for keyword, content in notes.items():
                f.write(f"## `{keyword}`\n\n")
                f.write(f"{content}\n\n")
                f.write("---\n\n")

        await e.client.send_file(
            e.chat_id,
            filename,
            caption=f"`[EXPORT-MD] {len(notes)} notes diekspor dalam format Markdown.`",
            reply_to=e.id,
        )
        await xx.delete()
    except Exception as err:
        LOGS.exception(err)
        await xx.edit(f"`[EXPORT-MD] Gagal: {err}`")
    finally:
        if os.path.exists(filename):
            os.remove(filename)
