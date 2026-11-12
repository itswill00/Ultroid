# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/TeamUltroid/pyUltroid/blob/main/LICENSE>.
"""
✘ Commands Available -

• `{i}effects [query]`
    List animated message effects available on Telegram (2026).

• `{i}effect <emoji|id> [text]`
    Send a message with an animated effect.
    Works in private chats / Saved Messages. Reply to a message
    to apply the effect to that message.

• `{i}date <when> [| text]`
    Send a live formatted date/time, rendered in each user's
    timezone and language by Telegram.

• `{i}countdown <when> [| text]`
    Send a live countdown that updates automatically.

• `{i}stars`
    Show your current Telegram Stars balance.
"""

import re
from datetime import datetime, timedelta

from telethon.tl.functions.messages import GetAvailableEffectsRequest
from telethon.tl.functions.payments import GetStarsStatusRequest
from telethon.tl.types import MessageEntityFormattedDate

from . import ultroid_cmd

_EFFECTS = []


async def _fetch_effects(client):
    """Fetch and cache the server-side animated effect catalog."""
    global _EFFECTS
    if _EFFECTS:
        return _EFFECTS
    response = await client(GetAvailableEffectsRequest(hash=0))
    effects = getattr(response, "effects", None)
    if effects is not None:
        _EFFECTS = effects
    return _EFFECTS


async def _safe_delete(event):
    try:
        await event.delete()
    except Exception:
        pass


async def _is_premium(client):
    try:
        me = await client.get_me()
        return bool(getattr(me, "premium", False))
    except Exception:
        return False


def _pick_effect(effects, query, premium):
    query = query.strip()
    allowed = [x for x in effects if premium or not x.premium_required]
    if not query:
        return None
    for effect in allowed:
        if str(effect.id) == query:
            return effect
    for effect in allowed:
        if effect.emoticon == query:
            return effect
    for effect in allowed:
        if query in effect.emoticon:
            return effect
    return None


@ultroid_cmd(pattern="effects( (.*)|$)")
async def list_effects(event):
    query = event.pattern_match.group(1).strip()
    effects = await _fetch_effects(event.client)
    if not effects:
        return await event.eor("`No effects available.`", time=10)
    premium = await _is_premium(event.client)
    pool = [x for x in effects if premium or not x.premium_required]
    if query:
        pool = [
            x for x in pool if query in x.emoticon or query in str(x.id)
        ]
    seen = set()
    unique = []
    for effect in pool:
        if effect.emoticon in seen:
            continue
        seen.add(effect.emoticon)
        unique.append(effect)
    if not unique:
        return await event.eor("`No matching effects.`", time=10)
    lines = [
        f"{x.emoticon}  `{x.id}`"
        for x in unique[:60]
    ]
    text = (
        f"**Animated Message Effects** ({len(unique)})\n\n"
        + "\n".join(lines)
        + "\n\nUse `.effect <emoji|id> <text>` in a private chat."
    )
    await event.eor(text, time=60)


@ultroid_cmd(pattern="effect( (.*)|$)")
async def send_effect(event):
    raw = event.pattern_match.group(1).strip()
    if not raw:
        return await event.eor(
            "**Usage:** `.effect <emoji|id> [text]`\n"
            "Reply to a message to apply it to that message.",
            time=10,
        )
    if not event.is_private:
        return await event.eor(
            "`Animated effects can only be used in private chats "
            "or Saved Messages.`",
            time=10,
        )
    parts = raw.split(maxsplit=1)
    query = parts[0]
    text = parts[1] if len(parts) > 1 else ""
    reply = await event.get_reply_message()
    effects = await _fetch_effects(event.client)
    premium = await _is_premium(event.client)
    effect = _pick_effect(effects, query, premium)
    if not effect:
        return await event.eor(
            "`Effect not found.` Use `.effects` to see available effects.",
            time=10,
        )
    if effect.premium_required and not premium:
        return await event.eor(
            "`That effect requires Telegram Premium.`",
            time=10,
        )
    if reply and not text:
        text = reply.raw_text or ""
    await _safe_delete(event)
    if reply and reply.media:
        return await event.client.send_file(
            event.chat_id,
            reply.media,
            caption=text,
            message_effect_id=effect.id,
            reply_to=reply.id,
        )
    await event.client.send_message(
        event.chat_id,
        text or effect.emoticon,
        message_effect_id=effect.id,
        reply_to=reply.id if reply else None,
        link_preview=False,
    )


_DATETIME_FORMATS = (
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%Y/%m/%d %H:%M",
    "%Y/%m/%d",
    "%Y-%m-%dT%H:%M",
    "%d-%m-%Y %H:%M",
    "%d-%m-%Y",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y",
    "%d.%m.%Y %H:%M",
    "%d.%m.%Y",
)


def _parse_when(raw):
    raw = raw.strip()
    now = datetime.now().astimezone()
    if raw.startswith("+"):
        units = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
        seconds = 0
        for amount, unit in re.findall(r"(\d+)\s*([smhdw])", raw[1:].lower()):
            seconds += int(amount) * units[unit]
        return now + timedelta(seconds=seconds) if seconds else None
    lowered = raw.lower()
    for prefix, days in (("tomorrow", 1), ("today", 0)):
        if lowered.startswith(prefix):
            rest = raw[len(prefix):].strip()
            date = (now + timedelta(days=days)).date()
            if not rest:
                return datetime.combine(date, datetime.min.time()).astimezone()
            try:
                time = datetime.strptime(rest, "%H:%M").time()
            except ValueError:
                return None
            return datetime.combine(date, time).astimezone()
    if re.fullmatch(r"\d{1,2}:\d{2}", raw):
        try:
            time = datetime.strptime(raw, "%H:%M").time()
        except ValueError:
            return None
        result = datetime.combine(now.date(), time).astimezone()
        if result <= now:
            result += timedelta(days=1)
        return result
    for fmt in _DATETIME_FORMATS:
        try:
            parsed = datetime.strptime(raw, fmt)
        except ValueError:
            continue
        return parsed.astimezone() if parsed.tzinfo is None else parsed
    return None


def _utf16_len(text):
    return len(text.encode("utf-16-le")) // 2


async def _send_formatted(event, relative):
    raw = event.pattern_match.group(1).strip()
    if not raw:
        return await event.eor(
            "**Usage:** `date <when> [| text]`\n"
            "Examples: `2026-12-31 23:59`, `tomorrow 10:00`, `+2h30m`.",
            time=10,
        )
    when_raw, _, text = raw.partition("|")
    when_raw = when_raw.strip()
    text = text.strip()
    parsed = _parse_when(when_raw)
    if not parsed:
        return await event.eor(
            "`Could not parse that date.` Try `2026-12-31 23:59`, "
            "`tomorrow 10:00`, or `+2h30m`.",
            time=10,
        )
    if text:
        label = when_raw
        full_text = f"{text}: {label}"
        offset = _utf16_len(f"{text}: ")
    else:
        label = when_raw
        full_text = label
        offset = 0
    if relative:
        entity = MessageEntityFormattedDate(
            offset=offset,
            length=_utf16_len(label),
            date=parsed,
            relative=True,
        )
    else:
        entity = MessageEntityFormattedDate(
            offset=offset,
            length=_utf16_len(label),
            date=parsed,
            long_date=True,
            short_time=True,
            day_of_week=True,
        )
    await _safe_delete(event)
    await event.client.send_message(
        event.chat_id,
        full_text,
        formatting_entities=[entity],
        link_preview=False,
        reply_to=event.reply_to_msg_id,
    )


@ultroid_cmd(pattern="date( (.*)|$)")
async def date_cmd(event):
    await _send_formatted(event, relative=False)


@ultroid_cmd(pattern="countdown( (.*)|$)")
async def countdown_cmd(event):
    await _send_formatted(event, relative=True)


@ultroid_cmd(pattern="stars$")
async def stars_cmd(event):
    try:
        peer = await event.client.get_input_entity("me")
        result = await event.client(GetStarsStatusRequest(peer=peer))
        balance = result.balance
        amount = getattr(balance, "amount", 0)
        nanos = getattr(balance, "nanos", 0)
        total = amount + (nanos / 1_000_000_000)
        await event.eor(
            f"⭐ **Telegram Stars**\n\nBalance: `{total:g}`",
            time=30,
        )
    except Exception as er:
        await event.eor(f"`Could not fetch Stars balance: {er}`", time=10)
