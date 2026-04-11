# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.
"""
✘ Commands Available -

• `{i}vault <label>`
    Reply ke pesan untuk menyimpannya ke vault dengan label tertentu.
    Contoh: `.vault password-wifi`

• `{i}vaultget <label>`
    Ambil pesan yang tersimpan di vault dengan label tersebut.

• `{i}vaultdel <label>`
    Hapus entri vault berdasarkan label.

• `{i}vaultlist`
    Lihat semua label yang tersimpan di vault.

• `{i}vaultclear`
    Hapus seluruh isi vault (konfirmasi diperlukan).

CATATAN: Vault disimpan di database bot (terenkripsi oleh mekanisme DB).
Jangan simpan sesitive credential di sini kecuali Anda percaya keamanan DB Anda.
"""

import json
from datetime import datetime

from . import udB, ultroid_cmd, LOGS

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
            "`[VAULT] Contoh: .vault password-wifi`\n"
            "`(Reply ke pesan yang ingin disimpan)`"
        )

    # Sanitize label
    label = label.lower().replace(" ", "-")[:50]

    reply = await e.get_reply_message()
    if not reply:
        return await e.eor("`[VAULT] Reply ke pesan yang ingin disimpan.`")

    content = reply.text or ""
    media_id = None

    # Jika pesan punya photo/document, simpan file_id
    if reply.media:
        try:
            from telethon.utils import pack_bot_file_id
            media_id = pack_bot_file_id(reply.media)
        except Exception:
            media_id = None

    if not content and not media_id:
        return await e.eor("`[VAULT] Pesan tidak memiliki konten yang bisa disimpan.`")

    vault = _get_vault()
    vault[label] = {
        "text": content,
        "media": media_id,
        "saved_at": datetime.now().strftime("%d %b %Y %H:%M:%S"),
        "chat_id": str(e.chat_id),
        "msg_id": reply.id,
    }
    _save_vault(vault)
    await e.eor(f"`[VAULT] Tersimpan dengan label: '{label}'`")


@ultroid_cmd(pattern="vaultget( (.*)|$)")
async def vault_get(e):
    label = e.pattern_match.group(1).strip().lower().replace(" ", "-")
    if not label:
        return await e.eor("`[VAULT] Contoh: .vaultget password-wifi`")

    vault = _get_vault()
    if label not in vault:
        return await e.eor(f"`[VAULT] Label '{label}' tidak ditemukan.`")

    entry = vault[label]
    text = entry.get("text", "")
    media = entry.get("media")
    saved_at = entry.get("saved_at", "?")

    header = f"**[VAULT] {label}**\nDisimpan: `{saved_at}`\n\n"
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
        await e.eor(f"`[VAULT] Gagal mengambil entri: {err}`")


@ultroid_cmd(pattern="vaultdel( (.*)|$)")
async def vault_del(e):
    label = e.pattern_match.group(1).strip().lower().replace(" ", "-")
    if not label:
        return await e.eor("`[VAULT] Contoh: .vaultdel password-wifi`")

    vault = _get_vault()
    if label not in vault:
        return await e.eor(f"`[VAULT] Label '{label}' tidak ditemukan.`")

    del vault[label]
    _save_vault(vault)
    await e.eor(f"`[VAULT] Label '{label}' dihapus dari vault.`")


@ultroid_cmd(pattern="vaultlist$")
async def vault_list(e):
    vault = _get_vault()
    if not vault:
        return await e.eor("`[VAULT] Vault kosong.`")

    lines = [f"**Vault — {len(vault)} entri:**\n"]
    for i, (label, entry) in enumerate(sorted(vault.items()), 1):
        typ = "📄 teks" if not entry.get("media") else "📎 media"
        saved = entry.get("saved_at", "?")
        lines.append(f"`{i:02d}.` **{label}** — {typ} — `{saved}`")

    await e.eor("\n".join(lines))


@ultroid_cmd(pattern="vaultclear( (.*)|$)")
async def vault_clear(e):
    confirm = e.pattern_match.group(1).strip()
    vault = _get_vault()
    if not vault:
        return await e.eor("`[VAULT] Vault sudah kosong.`")

    if confirm.lower() != "confirm":
        return await e.eor(
            f"`[VAULT] Vault memiliki {len(vault)} entri.`\n"
            "`Ketik .vaultclear confirm untuk menghapus semua.`"
        )

    udB.del_key(_VAULT_KEY)
    await e.eor("`[VAULT] Seluruh vault berhasil dihapus.`")
