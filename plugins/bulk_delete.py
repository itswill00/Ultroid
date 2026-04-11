# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.
"""
✘ Commands Available -

• `{i}bulkdel <jumlah>`
    Hapus N pesan terakhir Anda di chat saat ini.

• `{i}bulkdel <jumlah> all`
    Hapus N pesan terakhir siapapun (butuh hak admin di grup).

• `{i}bulkdel keyword <kata>`
    Hapus semua pesan yang mengandung kata tertentu (max 200 pesan diperiksa).

• `{i}purgefrom`
    Reply ke pesan lama, lalu hapus semua pesan dari situ hingga sekarang (milik Anda).
"""

import asyncio

from telethon.tl.functions.channels import DeleteMessagesRequest as ChannelDeleteMsg

from . import udB, ultroid_cmd, LOGS

help_bulkdelete = __doc__

_SAFE_LIMIT = 200  # Batas aman pengecekan pesan


@ultroid_cmd(pattern="bulkdel( (.*)|$)")
async def bulk_delete(e):
    args = e.pattern_match.group(1).strip().split()
    xx = await e.eor("`[BULK-DEL] Memproses...`")

    if not args:
        return await xx.edit(
            "`[BULK-DEL] Penggunaan: .bulkdel <jumlah> [all|keyword <kata>]`"
        )

    # Mode: hapus berdasarkan keyword
    if args[0].lower() == "keyword":
        if len(args) < 2:
            return await xx.edit("`[BULK-DEL] Contoh: .bulkdel keyword halo`")
        kw = " ".join(args[1:]).lower()
        to_delete = []
        async for msg in e.client.iter_messages(e.chat_id, limit=_SAFE_LIMIT):
            if msg.text and kw in msg.text.lower() and msg.out:
                to_delete.append(msg.id)

        if not to_delete:
            return await xx.edit(f"`[BULK-DEL] Tidak ada pesan milik Anda dengan kata '{kw}'.`")

        await e.client.delete_messages(e.chat_id, to_delete)
        return await xx.edit(f"`[BULK-DEL] {len(to_delete)} pesan dengan kata '{kw}' dihapus.`")

    # Mode: hapus N pesan
    try:
        count = int(args[0])
        count = min(count, _SAFE_LIMIT)
    except ValueError:
        return await xx.edit("`[BULK-DEL] Jumlah harus berupa angka.`")

    delete_all = len(args) > 1 and args[1].lower() == "all"

    to_delete = []
    async for msg in e.client.iter_messages(e.chat_id, limit=count if delete_all else _SAFE_LIMIT):
        if delete_all:
            to_delete.append(msg.id)
        elif msg.out:
            to_delete.append(msg.id)
        if not delete_all and len(to_delete) >= count:
            break

    if not to_delete:
        return await xx.edit("`[BULK-DEL] Tidak ada pesan yang bisa dihapus.`")

    try:
        await e.client.delete_messages(e.chat_id, to_delete)
        await xx.edit(f"`[BULK-DEL] {len(to_delete)} pesan berhasil dihapus.`")
    except Exception as err:
        LOGS.exception(err)
        await xx.edit(f"`[BULK-DEL] Gagal: {err}`")


@ultroid_cmd(pattern="purgefrom$")
async def purge_from(e):
    """Delete all your messages from replied message to current."""
    reply = await e.get_reply_message()
    if not reply:
        return await e.eor("`[PURGE] Reply ke pesan awal yang ingin dihapus.`")

    xx = await e.eor("`[PURGE] Menghapus pesan dari titik tersebut...`")
    from_id = reply.id
    to_id = e.id

    to_delete = []
    async for msg in e.client.iter_messages(
        e.chat_id, min_id=from_id - 1, max_id=to_id + 1
    ):
        if msg.out:
            to_delete.append(msg.id)

    if not to_delete:
        return await xx.edit("`[PURGE] Tidak ada pesan milik Anda di rentang tersebut.`")

    try:
        await e.client.delete_messages(e.chat_id, to_delete)
    except Exception as err:
        LOGS.exception(err)
        await xx.edit(f"`[PURGE] Gagal: {err}`")
