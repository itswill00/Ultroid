# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.
"""
✘ Commands Available -

• `{i}ask <pertanyaan>`
    Tanyakan sesuatu ke AI (Groq API). Membutuhkan GROQ_API_KEY di .env.

• `{i}summarize`
    Reply ke pesan atau rangkaian teks untuk meringkasnya.

• `{i}tldr <jumlah>`
    Baca <jumlah> pesan terakhir di chat dan buat ringkasan singkat.
    Contoh: `.tldr 50`

• `{i}aimodel <nama>`
    Ganti model AI. Default: llama-3.3-70b-versatile
    Model tersedia: llama-3.3-70b-versatile, mixtral-8x7b-32768, gemma2-9b-it
"""

import os
from datetime import datetime

from . import udB, ultroid_cmd, LOGS

help_smart_reply = __doc__

_DEFAULT_MODEL = "llama-3.3-70b-versatile"
_MODEL_KEY = "GROQ_AI_MODEL"
_MAX_TOKENS = 1024
_SYSTEM_PROMPT = (
    "You are a precise, technical assistant. "
    "Respond concisely and directly. "
    "Use Indonesian if the user writes in Indonesian, otherwise use English."
)


def _get_model() -> str:
    return udB.get_key(_MODEL_KEY) or _DEFAULT_MODEL


def _get_api_key() -> str | None:
    return udB.get_key("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")


async def _call_groq(prompt: str, system: str = _SYSTEM_PROMPT) -> str | None:
    """Call Groq API and return response text or None on failure."""
    api_key = _get_api_key()
    if not api_key:
        return None

    try:
        import aiohttp
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": _get_model(),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": _MAX_TOKENS,
            "temperature": 0.5,
        }
        async with aiohttp.ClientSession() as sess:
            async with sess.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    err = await resp.text()
                    LOGS.warning(f"[AI] Groq API error {resp.status}: {err[:200]}")
                    return None
                data = await resp.json()
                return data["choices"][0]["message"]["content"].strip()
    except Exception as err:
        LOGS.exception(err)
        return None


@ultroid_cmd(pattern="ask( (.*)|$)")
async def ask_ai(e):
    question = e.pattern_match.group(1).strip()

    # Optionally take question from replied message
    if not question:
        reply = await e.get_reply_message()
        if reply and reply.text:
            question = reply.text.strip()

    if not question:
        return await e.eor("`[AI] Contoh: .ask Apa itu machine learning?`")

    if not _get_api_key():
        return await e.eor(
            "`[AI] GROQ_API_KEY belum diset.`\n"
            "`Tambahkan ke .env: GROQ_API_KEY=gsk_xxx`"
        )

    xx = await e.eor("`[AI] Memproses...`")
    result = await _call_groq(question)

    if not result:
        return await xx.edit("`[AI] Tidak mendapat respons dari AI. Cek API key.`")

    model = _get_model()
    await xx.edit(
        f"**Pertanyaan:** {question[:200]}\n\n"
        f"**Jawaban:**\n{result}\n\n"
        f"`Model: {model}`"
    )


@ultroid_cmd(pattern="summarize$")
async def summarize_msg(e):
    reply = await e.get_reply_message()
    if not reply or not reply.text:
        return await e.eor("`[AI] Reply ke pesan yang ingin diringkas.`")

    if not _get_api_key():
        return await e.eor("`[AI] GROQ_API_KEY belum diset.`")

    xx = await e.eor("`[AI] Meringkas pesan...`")
    prompt = f"Ringkas pesan berikut dalam 2-3 kalimat singkat:\n\n{reply.text[:3000]}"
    result = await _call_groq(prompt)

    if not result:
        return await xx.edit("`[AI] Gagal mendapatkan ringkasan.`")

    await xx.edit(f"**Ringkasan:**\n{result}")


@ultroid_cmd(pattern="tldr( (.*)|$)")
async def tldr(e):
    match = e.pattern_match.group(1).strip()
    try:
        limit = max(5, min(int(match), 200)) if match.isdigit() else 50
    except Exception:
        limit = 50

    if not _get_api_key():
        return await e.eor("`[AI] GROQ_API_KEY belum diset.`")

    xx = await e.eor(f"`[AI] Membaca {limit} pesan terakhir...`")

    collected = []
    async for msg in e.client.iter_messages(e.chat_id, limit=limit):
        if msg.text and not msg.out:
            sender = getattr(msg.sender, "first_name", "?") or "?"
            collected.append(f"{sender}: {msg.text.strip()}")

    if not collected:
        return await xx.edit("`[AI] Tidak ada pesan teks untuk diringkas.`")

    await xx.edit("`[AI] Menganalisis percakapan...`")
    conversation = "\n".join(reversed(collected))[:4000]
    prompt = (
        "Berikut adalah percakapan dari sebuah grup Telegram. "
        "Buat ringkasan singkat (max 5 poin) tentang apa yang sedang dibahas:\n\n"
        f"{conversation}"
    )
    result = await _call_groq(prompt)

    if not result:
        return await xx.edit("`[AI] Gagal menganalisis percakapan.`")

    await xx.edit(
        f"**TL;DR — {limit} pesan terakhir:**\n\n{result}"
    )


@ultroid_cmd(pattern="aimodel( (.*)|$)")
async def set_ai_model(e):
    _VALID = ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "gemma2-9b-it"]
    model = e.pattern_match.group(1).strip()

    if not model:
        current = _get_model()
        return await e.eor(
            f"**Model AI saat ini:** `{current}`\n\n"
            f"**Tersedia:**\n" + "\n".join(f"• `{m}`" for m in _VALID)
        )

    if model not in _VALID:
        return await e.eor(
            f"`[AI] Model '{model}' tidak dikenali.`\n"
            f"Model tersedia: `{'`, `'.join(_VALID)}`"
        )

    udB.set_key(_MODEL_KEY, model)
    await e.eor(f"`[AI] Model diubah ke: {model}`")
