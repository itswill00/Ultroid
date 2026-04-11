# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.
"""
✘ Commands Available -

• `{i}bulkdel <count>`
    Delete the last N of your own messages in the current chat.

• `{i}bulkdel <count> all`
    Delete the last N messages from anyone (requires admin rights in groups).

• `{i}bulkdel keyword <word>`
    Delete all your messages containing a specific word (checks up to 200 messages).

• `{i}purgefrom`
    Reply to an old message, then delete all your messages from that point to current.
"""

import asyncio

from telethon.tl.functions.channels import DeleteMessagesRequest as ChannelDeleteMsg

from . import udB, ultroid_cmd, LOGS

help_bulkdelete = __doc__

_SAFE_LIMIT = 200  # Maximum messages to scan


@ultroid_cmd(pattern="bulkdel( (.*)|$)")
async def bulk_delete(e):
    args = e.pattern_match.group(1).strip().split()
    xx = await e.eor("`[BULK-DEL] Processing...`")

    if not args:
        return await xx.edit(
            "`[BULK-DEL] Usage: .bulkdel <count> [all|keyword <word>]`"
        )

    # Mode: delete by keyword
    if args[0].lower() == "keyword":
        if len(args) < 2:
            return await xx.edit("`[BULK-DEL] Example: .bulkdel keyword hello`")
        kw = " ".join(args[1:]).lower()
        to_delete = []
        async for msg in e.client.iter_messages(e.chat_id, limit=_SAFE_LIMIT):
            if msg.text and kw in msg.text.lower() and msg.out:
                to_delete.append(msg.id)

        if not to_delete:
            return await xx.edit(f"`[BULK-DEL] No outgoing messages found containing '{kw}'.`")

        await e.client.delete_messages(e.chat_id, to_delete)
        return await xx.edit(f"`[BULK-DEL] {len(to_delete)} message(s) containing '{kw}' deleted.`")

    # Mode: delete N messages
    try:
        count = int(args[0])
        count = min(count, _SAFE_LIMIT)
    except ValueError:
        return await xx.edit("`[BULK-DEL] Count must be a number.`")

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
        return await xx.edit("`[BULK-DEL] No messages available to delete.`")

    try:
        await e.client.delete_messages(e.chat_id, to_delete)
        await xx.edit(f"`[BULK-DEL] {len(to_delete)} message(s) deleted successfully.`")
    except Exception as err:
        LOGS.exception(err)
        await xx.edit(f"`[BULK-DEL] Failed: {err}`")


@ultroid_cmd(pattern="purgefrom$")
async def purge_from(e):
    """Delete all your messages from replied message to current."""
    reply = await e.get_reply_message()
    if not reply:
        return await e.eor("`[PURGE] Reply to the starting message you want to purge from.`")

    xx = await e.eor("`[PURGE] Deleting messages from that point...`")
    from_id = reply.id
    to_id = e.id

    to_delete = []
    async for msg in e.client.iter_messages(
        e.chat_id, min_id=from_id - 1, max_id=to_id + 1
    ):
        if msg.out:
            to_delete.append(msg.id)

    if not to_delete:
        return await xx.edit("`[PURGE] No outgoing messages found in that range.`")

    try:
        await e.client.delete_messages(e.chat_id, to_delete)
    except Exception as err:
        LOGS.exception(err)
        await xx.edit(f"`[PURGE] Failed: {err}`")
