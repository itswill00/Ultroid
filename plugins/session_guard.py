# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.
"""
✘ Commands Available -

• `{i}sessions`
    Lihat semua sesi aktif akun Telegram Anda.

• `{i}revoke <nomor>`
    Cabut sesi berdasarkan nomor dari daftar `.sessions`.

• `{i}revokeall`
    Cabut semua sesi aktif kecuali sesi saat ini.

• `{i}sessionguard on|off`
    Aktifkan/nonaktifkan pemantauan login baru.
    Jika aktif, bot akan mengirim alert ke LOG_CHANNEL jika ada login baru.
"""

import asyncio
from datetime import datetime

from telethon.tl.functions.account import (
    GetAuthorizationsRequest,
    ResetAuthorizationRequest,
    ResetAuthorizationsRequest,
)

from . import udB, ultroid_bot, ultroid_cmd, LOGS

help_session_guard = __doc__

_GUARD_KEY = "SESSION_GUARD"
_KNOWN_HASHES_KEY = "SESSION_KNOWN_HASHES"
_guard_task: asyncio.Task | None = None
_CHECK_INTERVAL = 300  # 5 menit


def _fmt_session(auth) -> str:
    country = getattr(auth, "country", "?")
    region = getattr(auth, "region", "")
    platform = getattr(auth, "platform", "?")
    device = getattr(auth, "device_model", "?")
    app = getattr(auth, "app_name", "?")
    date_active = getattr(auth, "date_active", None)
    date_str = date_active.strftime("%d %b %Y %H:%M") if date_active else "?"
    current = "✅ **[CURRENT]**" if getattr(auth, "current", False) else ""
    return (
        f"{current}\n"
        f"  Device:  `{device} ({platform})`\n"
        f"  App:     `{app}`\n"
        f"  Region:  `{region}, {country}`\n"
        f"  Active:  `{date_str}`\n"
        f"  Hash:    `{auth.hash}`"
    )


@ultroid_cmd(pattern="sessions$")
async def list_sessions(e):
    xx = await e.eor("`[SESSION] Mengambil daftar sesi...`")
    try:
        result = await e.client(GetAuthorizationsRequest())
        auths = result.authorizations
    except Exception as err:
        LOGS.exception(err)
        return await xx.edit(f"`[SESSION] Gagal: {err}`")

    if not auths:
        return await xx.edit("`[SESSION] Tidak ada sesi aktif.`")

    lines = [f"**Sesi Aktif ({len(auths)}):**\n"]
    for i, auth in enumerate(auths, 1):
        lines.append(f"**[{i}]** {_fmt_session(auth)}\n")

    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "\n...(terpotong)"
    await xx.edit(text)


@ultroid_cmd(pattern="revoke( (.*)|$)")
async def revoke_session(e):
    match = e.pattern_match.group(1).strip()
    if not match or not match.isdigit():
        return await e.eor("`[SESSION] Contoh: .revoke 2`\nGunakan .sessions untuk melihat daftar.")

    idx = int(match) - 1
    xx = await e.eor("`[SESSION] Mengambil daftar sesi...`")
    try:
        result = await e.client(GetAuthorizationsRequest())
        auths = result.authorizations
    except Exception as err:
        return await xx.edit(f"`[SESSION] Gagal mengambil sesi: {err}`")

    if idx < 0 or idx >= len(auths):
        return await xx.edit(f"`[SESSION] Nomor sesi tidak valid. Pilih 1-{len(auths)}.`")

    auth = auths[idx]
    if getattr(auth, "current", False):
        return await xx.edit("`[SESSION] Tidak bisa mencabut sesi yang sedang aktif.`")

    try:
        await e.client(ResetAuthorizationRequest(hash=auth.hash))
        await xx.edit(
            f"`[SESSION] Sesi #{match} berhasil dicabut.`\n"
            f"Device: `{auth.device_model}`"
        )
    except Exception as err:
        LOGS.exception(err)
        await xx.edit(f"`[SESSION] Gagal mencabut sesi: {err}`")


@ultroid_cmd(pattern="revokeall$")
async def revoke_all_sessions(e):
    xx = await e.eor("`[SESSION] Mencabut semua sesi lain...`")
    try:
        await e.client(ResetAuthorizationsRequest())
        await xx.edit("`[SESSION] Semua sesi selain sesi ini berhasil dicabut.`")
    except Exception as err:
        LOGS.exception(err)
        await xx.edit(f"`[SESSION] Gagal: {err}`")


@ultroid_cmd(pattern="sessionguard( (.*)|$)")
async def session_guard(e):
    global _guard_task
    action = e.pattern_match.group(1).strip().lower()
    log_ch = udB.get_key("LOG_CHANNEL")

    if action == "on":
        if not log_ch:
            return await e.eor("`[GUARD] LOG_CHANNEL belum diset.`")

        if _guard_task and not _guard_task.done():
            return await e.eor("`[GUARD] Session Guard sudah aktif.`")

        udB.set_key(_GUARD_KEY, "on")

        # Snapshot sesi saat ini
        try:
            result = await e.client(GetAuthorizationsRequest())
            known = {str(a.hash) for a in result.authorizations}
            udB.set_key(_KNOWN_HASHES_KEY, str(known))
        except Exception:
            known = set()

        async def _guard_loop():
            while True:
                await asyncio.sleep(_CHECK_INTERVAL)
                if udB.get_key(_GUARD_KEY) != "on":
                    break
                try:
                    result = await ultroid_bot(GetAuthorizationsRequest())
                    current_hashes = {str(a.hash) for a in result.authorizations}
                    stored = udB.get_key(_KNOWN_HASHES_KEY)
                    old_known = eval(stored) if stored else set()
                    new_sessions = current_hashes - old_known
                    if new_sessions:
                        # Login baru terdeteksi
                        for auth in result.authorizations:
                            if str(auth.hash) in new_sessions:
                                alert = (
                                    f"⚠️ **SESSION GUARD — Login Baru Terdeteksi**\n\n"
                                    f"{_fmt_session(auth)}\n\n"
                                    f"`{datetime.now().strftime('%d %b %Y %H:%M:%S')}`"
                                )
                                await ultroid_bot.send_message(log_ch, alert)
                        udB.set_key(_KNOWN_HASHES_KEY, str(current_hashes))
                except Exception as err:
                    LOGS.warning(f"[SESSION GUARD] Error: {err}")

        _guard_task = asyncio.get_event_loop().create_task(_guard_loop())
        await e.eor(
            f"`[GUARD] Session Guard diaktifkan.`\n"
            f"Interval: `{_CHECK_INTERVAL}s` · Alert ke LOG_CHANNEL."
        )

    elif action == "off":
        udB.set_key(_GUARD_KEY, "off")
        if _guard_task and not _guard_task.done():
            _guard_task.cancel()
            _guard_task = None
        await e.eor("`[GUARD] Session Guard dinonaktifkan.`")

    else:
        status = udB.get_key(_GUARD_KEY) or "off"
        is_running = bool(_guard_task and not _guard_task.done())
        await e.eor(
            f"**Session Guard**\n"
            f"Status: `{status}` · Running: `{is_running}`\n\n"
            f"Gunakan: `.sessionguard on` atau `.sessionguard off`"
        )
