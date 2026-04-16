# Ultroid - Database Backup & Restore Plugin
# Backup seluruh key-value DB ke Telegram (Log Channel)
# Restore dari file backup yang di-reply

from . import get_help

__doc__ = """
» Commands Available -

• `.backup`
    Backup semua data database ke Log Channel sebagai file JSON.
    Disertai tombol inline Restore & Info.

• `.restore` (reply ke file .json backup)
    Restore database dari file backup yang dikirim oleh .backup.
    Meminta konfirmasi sebelum menimpa data.

• `.dbinfo`
    Tampilkan ringkasan isi database (jumlah keys & nama).
"""

import json
import re as re_module
from datetime import datetime
from io import BytesIO

from telethon import Button

from pyUltroid._misc._assistant import callback

from . import (
    HNDLR,
    LOGS,
    asst,
    eod,
    eor,
    udB,
    ultroid_bot,
    ultroid_cmd,
)

# ──────────────────────────────────────────────────────────────
# Keys yang TIDAK di-backup (internal / sensitif / sementara)
# ──────────────────────────────────────────────────────────────
_SKIP_KEYS = {
    "_RESTART", "TGDB_URL", "LAST_UPDATE_LOG_SPAM",
    "INIT_DEPLOY", "KEEP_ACTIVE",
}

# ──────────────────────────────────────────────────────────────
# Pending restore sessions (user_id → payload dict)
# ──────────────────────────────────────────────────────────────
_PENDING_RESTORE = {}


# ──────────────────────────────────────────────────────────────
# Core Functions
# ──────────────────────────────────────────────────────────────

def _export_db() -> dict:
    """Ekspor semua key dari database ke dict Python."""
    data = {}
    for key in udB.keys():
        if key in _SKIP_KEYS:
            continue
        val = udB.get_key(key)
        data[key] = val
    return data


def _build_backup_bytes(data: dict) -> BytesIO:
    """Serialisasi data ke BytesIO berformat JSON."""
    payload = {
        "__meta__": {
            "db_name": udB.name,
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "total_keys": len(data),
            "version": "1.0",
        },
        "data": data,
    }
    buf = BytesIO(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str).encode("utf-8")
    )
    buf.name = f"ultroid_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    return buf


def _restore_db(payload: dict) -> tuple:
    """
    Restore keys dari payload backup.
    Returns: (restored_count, error_list)
    """
    data = payload.get("data", {})
    restored = 0
    errors = []
    for key, value in data.items():
        if key in _SKIP_KEYS:
            continue
        try:
            udB.set_key(key, value)
            restored += 1
        except Exception as e:
            errors.append(f"{key}: {e}")
    return restored, errors


# ──────────────────────────────────────────────────────────────
# Commands
# ──────────────────────────────────────────────────────────────

@ultroid_cmd(pattern="backup$", owner_only=True)
async def cmd_backup(event):
    """Backup database ke Log Channel dengan tombol inline."""
    log_ch = udB.get_key("LOG_CHANNEL")
    if not log_ch:
        return await eor(
            event, "`LOG_CHANNEL` belum di-set. Set dulu sebelum backup.", time=8
        )

    msg = await eor(event, "`⏳ Memproses backup database...`")

    try:
        data = _export_db()
        total_keys = len(data)

        if total_keys == 0:
            return await msg.edit("`Database kosong, tidak ada yang di-backup.`")

        buf = _build_backup_bytes(data)
        timestamp = datetime.utcnow().strftime("%d %b %Y %H:%M UTC")

        caption = (
            f"**🗄 Database Backup**\n\n"
            f"**DB:** `{udB.name}`\n"
            f"**Keys:** `{total_keys}`\n"
            f"**Waktu:** `{timestamp}`\n\n"
            f"▸ Reply file ini dengan `{HNDLR}restore` untuk memulihkan.\n"
            f"▸ Tekan tombol di bawah untuk aksi cepat."
        )

        sent = await asst.send_file(
            log_ch,
            file=buf,
            caption=caption,
            buttons=[
                [
                    Button.inline("📋 Info Keys", data="dbinfo"),
                ],
                [
                    Button.inline("🗑 Hapus Pesan Ini", data="dbdel"),
                ],
            ],
            force_document=True,
        )

        await msg.edit(
            f"**✅ Backup Berhasil!**\n\n"
            f"**{total_keys}** keys disimpan ke Log Channel.\n"
            f"[Lihat Backup]({sent.message_link})\n\n"
            f"Gunakan `{HNDLR}restore` (reply ke file itu) untuk restore.",
            link_preview=False,
        )

    except Exception as e:
        LOGS.exception(e)
        await msg.edit(f"**❌ Backup Gagal:**\n`{e}`")


@ultroid_cmd(pattern="restore$", fullsudo=True)
async def cmd_restore(event):
    """Restore database dari file backup JSON (reply ke file-nya)."""
    reply = await event.get_reply_message()

    if not reply or not reply.media:
        return await eod(
            event,
            f"`Reply ke file backup JSON, lalu jalankan {HNDLR}restore`",
            time=10,
        )

    msg = await eor(event, "`⏳ Membaca file backup...`")

    try:
        raw = await reply.download_media(bytes)
        payload = json.loads(raw.decode("utf-8"))

        meta = payload.get("__meta__", {})
        data = payload.get("data", {})

        if not isinstance(data, dict) or not data:
            return await msg.edit("`❌ File backup tidak valid atau kosong.`")

        db_name = meta.get("db_name", "Unknown")
        exported_at = meta.get("exported_at", "Unknown")
        total_keys = meta.get("total_keys", len(data))

        # Simpan untuk dipakai saat tombol dikonfirmasi
        _PENDING_RESTORE[event.sender_id] = payload

        # Tampilkan konfirmasi
        text = (
            f"**⚠️ Konfirmasi Restore**\n\n"
            f"**DB Asal:** `{db_name}`\n"
            f"**Waktu Backup:** `{exported_at}`\n"
            f"**Jumlah Keys:** `{total_keys}`\n\n"
            f"⚠️ **Ini akan menimpa data aktif!** Lanjutkan?"
        )
        buttons = [
            [
                Button.inline("✅ Ya, Restore", data="restore_confirm"),
                Button.inline("❌ Batal", data="restore_cancel"),
            ],
        ]

        if asst and asst.me.bot:
            # Gunakan Assistant Bot supaya tombol muncul (Userbot gak bisa tombol inline)
            await msg.delete()
            await asst.send_message(
                event.chat_id,
                text,
                buttons=buttons,
                reply_to=reply.id,
            )
        else:
            # Fallback jika asisten gak aktif (jarang terjadi di Dual Mode)
            await msg.edit(
                text + f"\n\n_Asisten tidak aktif. Gunakan `{HNDLR}ya` untuk konfirmasi manual._"
            )

    except json.JSONDecodeError:
        await msg.edit("`❌ File bukan JSON valid. Pastikan file adalah backup Ultroid.`")
    except Exception as e:
        LOGS.exception(e)
        await msg.edit(f"**❌ Gagal membaca backup:**\n`{e}`")


@ultroid_cmd(pattern="dbinfo$", fullsudo=True)
async def cmd_dbinfo(event):
    """Tampilkan ringkasan isi database."""
    msg = await eor(event, "`⏳ Mengambil info database...`")
    try:
        keys = sorted(k for k in udB.keys() if k not in _SKIP_KEYS)
        total = len(keys)

        if total == 0:
            return await msg.edit("`Database kosong.`")

        preview = "\n".join(f"• `{k}`" for k in keys[:50])
        suffix = f"\n_...dan {total - 50} keys lainnya_" if total > 50 else ""

        await msg.edit(
            f"**📋 Database Info — {udB.name}**\n\n"
            f"**Total Keys:** `{total}`\n\n"
            f"{preview}{suffix}\n\n"
            f"Gunakan `{HNDLR}backup` untuk backup semua ke Telegram.",
        )
    except Exception as e:
        LOGS.exception(e)
        await msg.edit(f"**❌ Error:**\n`{e}`")


# ──────────────────────────────────────────────────────────────
# Inline Button Callbacks (via assistant bot)
# ──────────────────────────────────────────────────────────────

@callback("dbinfo", owner=True)
async def cb_info(event):
    """Tombol Info Keys dari pesan backup di log channel."""
    try:
        keys = sorted(k for k in udB.keys() if k not in _SKIP_KEYS)
        total = len(keys)
        preview = ", ".join(keys[:25])
        suffix = f" ... +{total - 25} lainnya" if total > 25 else ""
        await event.answer(
            f"DB: {udB.name} | {total} Keys\n{preview}{suffix}",
            alert=True,
        )
    except Exception as e:
        await event.answer(f"Error: {e}", alert=True)


@callback("dbdel", owner=True)
async def cb_delete(event):
    """Tombol hapus pesan backup dari log channel."""
    try:
        await event.delete()
    except Exception as e:
        await event.answer(f"Gagal hapus: {e}", alert=True)


@callback("restore_confirm", owner=True)
async def cb_restore_confirm(event):
    """Konfirmasi restore — eksekusi penulisan ke database."""
    sender = event.sender_id
    payload = _PENDING_RESTORE.get(sender)

    if not payload:
        return await event.answer(
            "Session restore sudah expired. Jalankan .restore lagi.", alert=True
        )

    # Edit dulu supaya tombol hilang & user tau proses berjalan
    try:
        await event.edit("**⏳ Memulihkan database...**", buttons=None)
    except Exception:
        pass

    try:
        restored, errors = _restore_db(payload)
        meta = payload.get("__meta__", {})

        result = (
            f"**✅ Restore Selesai!**\n\n"
            f"**DB Asal:** `{meta.get('db_name', '?')}`\n"
            f"**Keys Dipulihkan:** `{restored}`\n"
        )
        if errors:
            err_preview = "\n".join(errors[:5])
            result += f"\n**⚠️ Error ({len(errors)}):**\n`{err_preview}`"

        result += "\n\n_Restart bot agar semua perubahan aktif._"

        try:
            await event.edit(result, buttons=None)
        except Exception:
            log_ch = udB.get_key("LOG_CHANNEL")
            if log_ch:
                await asst.send_message(log_ch, result)

        _PENDING_RESTORE.pop(sender, None)

    except Exception as e:
        LOGS.exception(e)
        try:
            await event.edit(f"**❌ Restore Gagal:**\n`{e}`", buttons=None)
        except Exception:
            pass


@callback("restore_cancel", owner=True)
async def cb_restore_cancel(event):
    """Batal restore."""
    _PENDING_RESTORE.pop(event.sender_id, None)
    try:
        await event.edit("`❌ Restore dibatalkan.`", buttons=None)
    except Exception:
        await event.answer("Restore dibatalkan.", alert=True)


# ──────────────────────────────────────────────────────────────
# Background Tasks (Self-Healing Backup)
# ──────────────────────────────────────────────────────────────
import asyncio

async def auto_backup_loop():
    """Jalankan backup otomatis setiap 24 jam."""
    while True:
        await asyncio.sleep(86400)  # 24 Jam
        try:
            log_ch = udB.get_key("LOG_CHANNEL")
            if not log_ch:
                continue

            data = _export_db()
            if len(data) == 0:
                continue

            buf = _build_backup_bytes(data)
            timestamp = datetime.utcnow().strftime("%d %b %Y %H:%M UTC")

            caption = (
                f"**🔄 Auto-Backup Database**\n\n"
                f"**DB:** `{udB.name}`\n"
                f"**Keys:** `{len(data)}`\n"
                f"**Waktu:** `{timestamp}`\n\n"
                f"▸ Reply file ini dengan `{HNDLR}restore` untuk memulihkan."
            )

            await asst.send_file(
                log_ch,
                file=buf,
                caption=caption,
                buttons=[[Button.inline("📋 Info Keys", data="dbinfo")]],
                force_document=True,
                silent=True, # Jangan ganggu user dengan suara notifikasi
            )
            LOGS.info("Auto-Backup: Database successfully backed up to Log Channel.")
        except Exception as e:
            LOGS.warning(f"Auto-Backup failed: {e}")

# Start background backup if not already running
if not hasattr(udB, "_autobackup_started"):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(auto_backup_loop())
        else:
            asyncio.ensure_future(auto_backup_loop())
    except Exception:
        pass
    udB._autobackup_started = True
