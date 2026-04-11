# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.
"""
✘ Commands Available -

• `{i}logwatch start`
    Mulai pantau ultroid.log dan kirim error baru ke LOG_CHANNEL secara otomatis.

• `{i}logwatch stop`
    Hentikan pemantauan log.

• `{i}logwatch status`
    Cek status pemantauan log.

• `{i}sendlog`
    Kirim isi log terbaru (200 baris terakhir) ke LOG_CHANNEL.

• `{i}clearlog`
    Hapus isi file ultroid.log.
"""

import asyncio
import os
from datetime import datetime

from . import udB, ultroid_bot, ultroid_cmd, LOGS

help_log_watcher = __doc__

_LOG_FILE = "ultroid.log"
_TAIL_LINES = 200
_WATCH_INTERVAL = 30  # detik
_watch_task: asyncio.Task | None = None
_last_size: int = 0
_seen_errors: set = set()


def _read_tail(filepath: str, lines: int = 50) -> str:
    """Read last N lines of a file efficiently."""
    try:
        with open(filepath, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            if size == 0:
                return ""
            # Read from end
            block = min(size, lines * 120)
            f.seek(-block, 2)
            content = f.read().decode("utf-8", errors="replace")
            return "\n".join(content.splitlines()[-lines:])
    except FileNotFoundError:
        return ""
    except Exception as err:
        return f"Error reading log: {err}"


def _extract_errors(content: str) -> list[str]:
    """Extract unique error blocks from log content."""
    errors = []
    lines = content.splitlines()
    in_error = False
    current = []
    for line in lines:
        if any(k in line for k in ("ERROR", "CRITICAL", "Traceback", "Exception")):
            in_error = True
        if in_error:
            current.append(line)
            if line.strip() == "" and current:
                block = "\n".join(current).strip()
                if block and block not in _seen_errors:
                    _seen_errors.add(block)
                    errors.append(block)
                current = []
                in_error = False
    return errors


@ultroid_cmd(pattern="logwatch( (.*)|$)")
async def log_watch(e):
    global _watch_task, _last_size
    action = e.pattern_match.group(1).strip().lower()
    log_ch = udB.get_key("LOG_CHANNEL")

    if action == "start":
        if _watch_task and not _watch_task.done():
            return await e.eor("`[LOGWATCH] Sudah aktif. Gunakan .logwatch stop untuk menghentikan.`")
        if not log_ch:
            return await e.eor("`[LOGWATCH] LOG_CHANNEL belum diset.`")

        _last_size = os.path.getsize(_LOG_FILE) if os.path.exists(_LOG_FILE) else 0
        _seen_errors.clear()

        async def _watcher():
            global _last_size
            while True:
                await asyncio.sleep(_WATCH_INTERVAL)
                if not os.path.exists(_LOG_FILE):
                    continue
                current_size = os.path.getsize(_LOG_FILE)
                if current_size <= _last_size:
                    continue
                # Read new content only
                try:
                    with open(_LOG_FILE, "rb") as f:
                        f.seek(_last_size)
                        new_content = f.read().decode("utf-8", errors="replace")
                    _last_size = current_size
                    new_errors = _extract_errors(new_content)
                    for err_block in new_errors[:3]:  # max 3 per cycle
                        truncated = err_block[:3500]
                        try:
                            await ultroid_bot.send_message(
                                log_ch,
                                f"⚠️ **Log Error Detected**\n"
                                f"`{datetime.now().strftime('%d %b %Y %H:%M:%S')}`\n\n"
                                f"```\n{truncated}\n```",
                            )
                        except Exception as send_err:
                            LOGS.warning(f"[LOGWATCH] Gagal kirim error: {send_err}")
                except Exception:
                    pass

        _watch_task = asyncio.get_event_loop().create_task(_watcher())
        await e.eor(
            f"`[LOGWATCH] Aktif — memeriksa error setiap {_WATCH_INTERVAL} detik.`"
        )

    elif action == "stop":
        if _watch_task and not _watch_task.done():
            _watch_task.cancel()
            _watch_task = None
            await e.eor("`[LOGWATCH] Pemantauan dihentikan.`")
        else:
            await e.eor("`[LOGWATCH] Tidak ada pemantauan aktif.`")

    elif action == "status":
        is_active = bool(_watch_task and not _watch_task.done())
        status = "✅ Aktif" if is_active else "⭕ Tidak aktif"
        sz = os.path.getsize(_LOG_FILE) if os.path.exists(_LOG_FILE) else 0
        await e.eor(
            f"**Log Watcher**\n"
            f"Status: {status}\n"
            f"File: `{_LOG_FILE}` ({sz / 1024:.1f} KB)\n"
            f"Interval: `{_WATCH_INTERVAL}s`"
        )
    else:
        await e.eor("`[LOGWATCH] Gunakan: .logwatch start | stop | status`")


@ultroid_cmd(pattern="sendlog$")
async def send_log(e):
    log_ch = udB.get_key("LOG_CHANNEL")
    if not log_ch:
        return await e.eor("`[LOG] LOG_CHANNEL belum diset.`")
    if not os.path.exists(_LOG_FILE):
        return await e.eor(f"`[LOG] File {_LOG_FILE} tidak ditemukan.`")

    xx = await e.eor("`[LOG] Mengirim log...`")
    content = _read_tail(_LOG_FILE, _TAIL_LINES)
    if not content:
        return await xx.edit("`[LOG] File log kosong.`")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    tmp = f"ultroid_log_{ts}.txt"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(content)
        await ultroid_bot.send_file(
            log_ch,
            tmp,
            caption=f"`[LOG] {_TAIL_LINES} baris terakhir — {datetime.now().strftime('%d %b %Y %H:%M:%S')}`",
        )
        await xx.edit("`[LOG] Log berhasil dikirim ke LOG_CHANNEL.`")
    except Exception as err:
        LOGS.exception(err)
        await xx.edit(f"`[LOG] Gagal: {err}`")
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


@ultroid_cmd(pattern="clearlog$")
async def clear_log(e):
    if not os.path.exists(_LOG_FILE):
        return await e.eor(f"`[LOG] File {_LOG_FILE} tidak ditemukan.`")
    try:
        open(_LOG_FILE, "w").close()
        await e.eor("`[LOG] File ultroid.log berhasil dibersihkan.`")
    except Exception as err:
        await e.eor(f"`[LOG] Gagal: {err}`")
