# Ultroid - Assistant Tools
# Part of Universal Assistant Control Suite

import json
from datetime import datetime
from telethon import events
from telethon.utils import get_peer_id

from . import asst, asst_cmd, udB, ultroid_bot
from pyUltroid.fns.helper import time_formatter

@asst_cmd(pattern="id")
async def assistant_id(event):
    """Extract IDs of users, chats, and replied media."""
    text = f"🛡️ **System Identification**\n---"
    text += f"\n📍 **Chat ID:** `{event.chat_id}`"
    text += f"\n👤 **User ID:** `{event.sender_id}`"
    
    if event.is_reply:
        reply = await event.get_reply_message()
        if reply.sender_id:
            text += f"\n👤 **Replied User:** `{reply.sender_id}`"
        if reply.media:
            text += f"\n📦 **Media ID:** `{get_peer_id(reply.media)}`" if hasattr(reply.media, 'media') else "\n📦 **Media Detected**"

    text += f"\n---\n⚙️ `Secure Identity Ledger`"
    await event.reply(text)

@asst_cmd(pattern="info")
async def assistant_info(event):
    """Basic profile audit via Assistant."""
    target = event.sender_id
    if event.is_reply:
        reply = await event.get_reply_message()
        target = reply.sender_id
    
    chat = await event.client.get_entity(target)
    
    first = getattr(chat, 'first_name', 'N/A')
    last = getattr(chat, 'last_name', '')
    user = getattr(chat, 'username', 'No Username')
    bio = getattr(chat, 'about', 'No Bio')
    
    text = (
        f"👤 **System Identification: Profile**\n"
        f"---"
        f"\n**First:** {first}"
        f"\n**Last:** {last}"
        f"\n**Username:** @{user}"
        f"\n**ID:** `{chat.id}`"
        f"\n**Bio:** `{bio}`"
        f"\n---"
        f"\n⚙️ `Global Profile Scoping`"
    )
    await event.reply(text)

@asst_cmd(pattern="json")
async def assistant_json(event):
    """Raw metadata audit for debugging."""
    if not event.is_reply:
        return await event.reply("`Reply to a message to audit its raw JSON metadata.`")
    
    reply = await event.get_reply_message()
    try:
        raw = reply.to_json(indent=4)
        if len(raw) > 4000:
            # Handle large JSON by sending as file
            with open("metadata.json", "w") as f:
                f.write(raw)
            await event.reply("**[ 📑 Message Metadata ]**", file="metadata.json")
            import os
            os.remove("metadata.json")
        else:
            await event.reply(f"**[ 📑 Message Metadata ]**\n```json\n{raw}\n```")
    except Exception as e:
        await event.reply(f"❌ **Metadata Retrieval Failed:** `{str(e)}`")
