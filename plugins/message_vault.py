# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

from . import get_help
__doc__ = get_help("message_vault")

"""
» Commands Available -

• `{i}vault <label>`
    Reply to a message to save it to the vault with the given label.
    Example: `.vault wifi-password`

• `{i}vaultget <label>`
    Retrieve a saved vault entry by its label.

• `{i}vaultdel <label>`
    Delete a vault entry by its label.

• `{i}vaultlist`
    Show all labels currently stored in the vault.

• `{i}vaultclear`
    Delete all vault entries (requires confirmation).

NOTE: Vault entries are stored in the bot's database.
Do not store sensitive credentials unless you trust your DB backend security.
"""

import json
from datetime import datetime

from . import LOGS, udB, ultroid_cmd

help_message_vault = __doc__

_VAULT_KEY = "MSG_VAULT"


def _get_vault() -> dict:
    raw = udB.get_key(_VAULT_KEY)
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(str(raw))
    except Exception:
        return {}


def _save_vault(vault: dict):
    udB.set_key(_VAULT_KEY, json.dumps(vault, ensure_ascii=False))


@ultroid_cmd(pattern="vault( (.*)|$)")
async def vault_save(e):
    label = e.pattern_match.group(1).strip()
    if not label:
        return await e.eor(
            "`Vault | Example: .vault wifi-password`\n"
            "`(Reply to the message you want to save)`"
        )

    # Sanitize label
    label = label.lower().replace(" ", "-")[:50]

    reply = await e.get_reply_message()
    if not reply:
        return await e.eor("`Vault | Reply to the message you want to save.`")

    content = reply.text or ""
    media_id = None

    # If the message has media, store its file_id
    if reply.media:
        try:
            from telethon.utils import pack_bot_file_id
            media_id = pack_bot_file_id(reply.media)
        except Exception:
            media_id = None

    if not content and not media_id:
        return await e.eor("`Vault | Message has no storable content.`")

    vault = _get_vault()
    vault[label] = {
        "text": content,
        "media": media_id,
        "saved_at": datetime.now().strftime("%d %b %Y %H:%M:%S"),
        "chat_id": str(e.chat_id),
        "msg_id": reply.id,
    }
    _save_vault(vault)
    await e.eor(f"`Vault | Saved under label: '{label}'`")


@ultroid_cmd(pattern="vaultget( (.*)|$)")
async def vault_get(e):
    label = e.pattern_match.group(1).strip().lower().replace(" ", "-")
    if not label:
        return await e.eor("`Vault | Example: .vaultget wifi-password`")

    vault = _get_vault()
    if label not in vault:
        return await e.eor(f"`Vault | Label '{label}' not found.`")

    entry = vault[label]
    text = entry.get("text", "")
    media = entry.get("media")
    saved_at = entry.get("saved_at", "?")

    header = f"**Vault | {label}**\nSaved: `{saved_at}`\n\n"
    try:
        if media:
            await e.client.send_file(
                e.chat_id,
                media,
                caption=header + text,
                reply_to=e.id,
            )
            await e.delete()
        else:
            await e.eor(header + text)
    except Exception as err:
        LOGS.exception(err)
        await e.eor(f"`Vault | Failed to retrieve entry: {err}`")


@ultroid_cmd(pattern="vaultdel( (.*)|$)")
async def vault_del(e):
    label = e.pattern_match.group(1).strip().lower().replace(" ", "-")
    if not label:
        return await e.eor("`Vault | Example: .vaultdel wifi-password`")

    vault = _get_vault()
    if label not in vault:
        return await e.eor(f"`Vault | Label '{label}' not found.`")

    del vault[label]
    _save_vault(vault)
    await e.eor(f"`Vault | Label '{label}' deleted from vault.`")


@ultroid_cmd(pattern="vaultlist$")
async def vault_list(e):
    vault = _get_vault()
    if not vault:
        return await e.eor("`Vault | Vault is empty.`")

    lines = [f"**Vault — {len(vault)} entry/entries:**\n"]
    for i, (label, entry) in enumerate(sorted(vault.items()), 1):
        typ = "📄 text" if not entry.get("media") else "📎 media"
        saved = entry.get("saved_at", "?")
        lines.append(f"`{i:02d}.` **{label}** — {typ} — `{saved}`")

    await e.eor("\n".join(lines))


@ultroid_cmd(pattern="vaultclear( (.*)|$)")
async def vault_clear(e):
    confirm = e.pattern_match.group(1).strip()
    vault = _get_vault()
    if not vault:
        return await e.eor("`Vault | Vault is already empty.`")

    if confirm.lower() != "confirm":
        return await e.eor(
            f"`Vault | Vault has {len(vault)} entry/entries.`\n"
            "`Type .vaultclear confirm to delete all.`"
        )

    udB.del_key(_VAULT_KEY)
    await e.eor("`Vault | All vault entries deleted.`")