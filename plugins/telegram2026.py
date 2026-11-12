# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/TeamUltroid/pyUltroid/blob/main/LICENSE/>.
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

• `{i}rank <tag>`
    Set a participant's group tag/rank (reply to them).

• `{i}poll2 <question> ; <option> ; <option> | [flags]`
    Polls with the 2026 features: quiz with several correct answers,
    shuffle, no-revote, hidden results, auto-close, country filter,
    solution and explanation media.
    Flags (comma separated):
      `quiz` / `quiz=1,3`   correct answers (1-based)
      `multi`               multiple choice
      `shuffle` `norevote` `hidden`
      `public`
      `close=1h`            `30s`, `10m`, `2h`, `7d`
      `countries=ID,MY`
      `solution=...`        explanation shown after answering
      `=media`              attach a photo/video (album, caption, reply)
      `=solution_media`     attach a photo/video to the explanation

• `{i}storyarchive [count]`
    List your own story archive.

• `{i}storyreact <link|id> [emoji]`
    React to a story (default 🔥).

• `{i}storysave <link|id>`
    Save a photo/video story to Saved Messages.

• `{i}gifts [limited]`
    Show the Telegram Stars gift catalog and prices.

• `{i}mygifts`
    Show the gifts you have received.

• `{i}todo <title> ; item ; item`
    Create a native collaborative checklist (requires Premium).

• `{i}stars`
    Show your Telegram Stars and TON balance.
"""

import os
import re
from datetime import datetime, timedelta

from telethon.tl.functions.messages import (
    EditChatParticipantRankRequest,
    GetAvailableEffectsRequest,
    SendMediaRequest,
)
from telethon.tl.functions.payments import (
    GetSavedStarGiftsRequest,
    GetStarGiftsRequest,
    GetStarsStatusRequest,
)
from telethon.tl.functions.stories import (
    GetStoriesArchiveRequest,
    GetStoriesByIDRequest,
    SendReactionRequest,
)
from telethon.tl.types import (
    InputMediaPoll,
    InputMediaTodo,
    MessageEntityFormattedDate,
    MessageMediaDocument,
    MessageMediaPhoto,
    Poll,
    PollAnswer,
    ReactionEmoji,
    StoryItem,
    TextWithEntities,
    TodoItem,
    TodoList,
)

from . import ultroid_cmd

_EFFECTS = []
_STORY_LINK = re.compile(r"https?://t\.me/(?:s/)?(?:c/)?([^/?]+)(?:/s/|/)(\d+)")
_COUNTRIES = re.compile(r"^(?:countries|country)=(.+)$")


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
        pool = [x for x in pool if query in x.emoticon or query in str(x.id)]
    seen = set()
    unique = []
    for effect in pool:
        if effect.emoticon in seen:
            continue
        seen.add(effect.emoticon)
        unique.append(effect)
    if not unique:
        return await event.eor("`No matching effects.`", time=10)
    lines = [f"{x.emoticon}  `{x.id}`" for x in unique[:60]]
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
        return await event.eor("`That effect requires Telegram Premium.`", time=10)
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

_DURATION_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}


def _parse_when(raw):
    raw = raw.strip()
    now = datetime.now().astimezone()
    if raw.startswith("+"):
        seconds = 0
        for amount, unit in re.findall(r"(\d+)\s*([smhdw])", raw[1:].lower()):
            seconds += int(amount) * _DURATION_UNITS[unit]
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


def _parse_duration(raw):
    raw = raw.strip().lower()
    if raw.isdigit():
        return int(raw)
    seconds = 0
    for amount, unit in re.findall(r"(\d+)\s*([smhdw])", raw):
        seconds += int(amount) * _DURATION_UNITS[unit]
    return seconds or None


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
    label = when_raw
    if text:
        full_text = f"{text}: {label}"
        offset = _utf16_len(f"{text}: ")
    else:
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


@ultroid_cmd(pattern="rank( (.*)|$)")
async def rank_cmd(event):
    if not event.is_group:
        return await event.eor("`Use this in a group.`", time=8)
    reply = await event.get_reply_message()
    if not reply:
        return await event.eor(
            "**Usage:** `.rank <tag>` (reply to a member)\n"
            "Max 16 characters, no emojis.",
            time=10,
        )
    rank = event.pattern_match.group(1).strip()
    if not rank:
        return await event.eor(
            "**Usage:** `.rank <tag>` (reply to a member)", time=10
        )
    if len(rank) > 16:
        return await event.eor("`A rank can be at most 16 characters.`", time=8)
    try:
        await event.client(
            EditChatParticipantRankRequest(
                peer=event.chat_id,
                participant=reply.sender_id,
                rank=rank,
            )
        )
        await event.eor(f"✅ Rank set to `{rank}`.", time=10)
    except Exception as er:
        await event.eor(f"`Failed to set rank: {er}`", time=10)


# --------------------------------------------------------------------------
# Polls 2026
# --------------------------------------------------------------------------


def _parse_poll_args(raw):
    """Split ``question ; options | flags`` into its components."""
    flags_raw = ""
    body = raw
    if "|" in raw:
        body, _, flags_raw = raw.partition("|")
    if ";" not in body:
        return None
    question, *options = [x.strip() for x in body.split(";")]
    options = [x for x in options if x]
    flags = [x.strip() for x in flags_raw.split(",") if x.strip()]
    return question.strip(), options, flags


def _make_poll(question, options, flags_set, correct, countries, close_seconds):
    answers = [
        PollAnswer(TextWithEntities(option, []), str(index).encode())
        for index, option in enumerate(options)
    ]
    kwargs = dict(
        id=0,
        question=TextWithEntities(question, []),
        answers=answers,
        hash=0,
        quiz="quiz" in flags_set,
        multiple_choice="multi" in flags_set,
        public_voters="public" in flags_set,
        revoting_disabled="norevote" in flags_set,
        shuffle_answers="shuffle" in flags_set,
        hide_results_until_close="hidden" in flags_set,
        open_answers="open" in flags_set,
        countries_iso2=countries,
    )
    if close_seconds:
        kwargs["close_period"] = close_seconds
    return Poll(**kwargs)


@ultroid_cmd(pattern="poll2( (.*)|$)")
async def poll2026(event):
    raw = event.pattern_match.group(1).strip()
    parsed = _parse_poll_args(raw)
    if not parsed:
        return await event.eor(
            "**Usage:** `.poll2 question ; option ; option | flags`\n"
            "Example: `.poll2 Favourite? ; Pizza ; Sushi | quiz=2,multi,shuffle`",
            time=15,
        )
    question, options, flags = parsed
    if len(options) < 1:
        return await event.eor("`Need at least one option.`", time=10)

    correct = []
    solution = None
    close_seconds = None
    countries = None
    flags_set = set()
    want_media = want_solution_media = False
    for flag in flags:
        lowered = flag.lower()
        if lowered == "media":
            want_media = True
        elif lowered == "solution_media":
            want_solution_media = True
        elif lowered.startswith("quiz="):
            flags_set.add("quiz")
            for part in lowered.split("=", 1)[1].split("+"):
                if part.strip().isdigit():
                    correct.append(int(part.strip()) - 1)
        elif lowered == "quiz":
            flags_set.add("quiz")
        elif lowered.startswith("solution="):
            solution = flag.split("=", 1)[1].strip() or None
        elif lowered.startswith("close="):
            close_seconds = _parse_duration(lowered.split("=", 1)[1])
        elif _COUNTRIES.match(lowered):
            countries = [
                x.strip().upper()
                for x in _COUNTRIES.match(lowered).group(1).split("+")
                if x.strip()
            ]
        elif lowered in ("multi", "shuffle", "norevote", "hidden", "public", "open"):
            flags_set.add(lowered)

    if correct and not flags_set & {"multi"} and len(correct) > 1:
        return await event.eor(
            "`Multiple correct answers need the `multi` flag.`", time=10
        )
    if "quiz" in flags_set and not correct:
        correct = [0]

    media = solution_media = None
    reply = await event.get_reply_message()
    if reply and reply.media:
        if want_solution_media:
            solution_media = reply.media
        elif want_media:
            media = reply.media

    poll = _make_poll(
        question, options, flags_set, correct, countries, close_seconds
    )
    input_media = InputMediaPoll(
        poll,
        correct_answers=correct or None,
        attached_media=media,
        solution=solution,
        solution_entities=[] if solution else None,
        solution_media=solution_media,
    )
    caption = None
    if reply and reply.media and (media or solution_media):
        caption = reply.raw_text or None
    try:
        await event.client.send_file(
            event.chat_id,
            file=input_media,
            caption=caption,
            reply_to=event.reply_to_msg_id if not reply else None,
        )
    except Exception as er:
        if "COUNTRIES" in str(er).upper():
            return await event.eor(
                "`Country-restricted polls are not allowed in this chat.`", time=10
            )
        return await event.eor(f"`Could not create poll: {er}`", time=12)
    await _safe_delete(event)


# --------------------------------------------------------------------------
# Stories
# --------------------------------------------------------------------------


async def _resolve_story(event, raw):
    """Resolve ``<link|id>`` into ``(peer, story_id)``.

    A bare numeric id refers to a story of the account itself
    (Saved Messages) unless the current chat is a channel/group
    with visible stories.
    """
    raw = raw.strip()
    match = _STORY_LINK.search(raw)
    if match:
        peer = match.group(1)
        return peer, int(match.group(2))
    if raw.isdigit():
        chat = await event.get_chat()
        if getattr(chat, "broadcast", False) or getattr(chat, "megagroup", False):
            return event.chat_id, int(raw)
        return "me", int(raw)
    return None, None


async def _fresh_story(client, peer, story_id):
    """Fetch a story's media with a fresh file reference."""
    input_peer = await client.get_input_entity(peer)
    result = await client(
        GetStoriesByIDRequest(peer=input_peer, id=[story_id])
    )
    for item in getattr(result, "stories", []):
        if isinstance(item, StoryItem) and getattr(item, "id", None) == story_id:
            return item
    return None


def _story_link(item, peer):
    username = getattr(peer, "username", None)
    if not username:
        return ""
    return f"https://t.me/{username}/s/{item.id}"


@ultroid_cmd(pattern="storyarchive( (.*)|$)")
async def story_archive(event):
    raw = event.pattern_match.group(1).strip()
    limit = int(raw) if raw.isdigit() else 5
    limit = max(1, min(limit, 20))
    me = await event.client.get_input_entity("me")
    try:
        result = await event.client(
            GetStoriesArchiveRequest(peer=me, offset_id=0, limit=limit)
        )
    except Exception as er:
        return await event.eor(f"`Could not load archive: {er}`", time=12)
    items = [x for x in result.stories if isinstance(x, StoryItem)]
    if not items:
        return await event.eor("`Your story archive is empty.`", time=10)
    self_entity = await event.client.get_entity("me")
    lines = []
    for item in items:
        date = item.date.strftime("%Y-%m-%d %H:%M") if item.date else "?"
        kind = "🎬" if isinstance(item.media, MessageMediaDocument) else "🖼"
        views = getattr(getattr(item, "views", None), "views_count", 0) or 0
        link = _story_link(item, self_entity)
        caption = (item.caption or "").replace("\n", " ")[:40]
        entry = f"{kind} `{item.id}`  {date}  👁 {views}"
        if caption:
            entry += f"\n     {caption}"
        if link:
            entry += f"\n     [{kind} open]({link})"
        lines.append(entry)
    text = (
        f"**Your Story Archive** ({result.count} total, showing {len(items)})\n\n"
        + "\n".join(lines)
    )
    await event.eor(text, time=60, link_preview=False)


@ultroid_cmd(pattern="storyreact( (.*)|$)")
async def story_react(event):
    raw = event.pattern_match.group(1).strip()
    if not raw:
        return await event.eor(
            "**Usage:** `.storyreact <link|id> [emoji]`", time=10
        )
    parts = raw.split(maxsplit=1)
    peer, story_id = await _resolve_story(event, parts[0])
    if not peer:
        return await event.eor("`Invalid story link or id.`", time=10)
    emoji = parts[1].strip() if len(parts) > 1 else "🔥"
    if not emoji:
        emoji = "🔥"
    try:
        await event.client(
            SendReactionRequest(
                peer=peer,
                story_id=story_id,
                reaction=ReactionEmoji(emoji),
                add_to_recent=True,
            )
        )
        await event.eor(f"✅ Reacted {emoji} to story `{story_id}`.", time=10)
    except Exception as er:
        if "STORIES_NEVER_CREATED" in str(er) or "STORY_NOT_FOUND" in str(er):
            return await event.eor(
                "`That story is no longer active (expired or archived).`",
                time=10,
            )
        await event.eor(f"`Could not react: {er}`", time=12)


@ultroid_cmd(pattern="storysave( (.*)|$)")
async def story_download(event):
    raw = event.pattern_match.group(1).strip()
    if not raw:
        return await event.eor("**Usage:** `.storysave <link|id>`", time=10)
    peer, story_id = await _resolve_story(event, raw)
    if not peer:
        return await event.eor("`Invalid story link or id.`", time=10)
    status = await event.eor("`Downloading story...`")
    try:
        try:
            item = await _fresh_story(event.client, peer, story_id)
        except Exception:
            return await status.edit("`Story not found.`")
        if not item:
            return await status.edit("`Story not found.`")
        if not isinstance(item.media, (MessageMediaPhoto, MessageMediaDocument)):
            return await status.edit("`Unsupported story media.`")
        path = await event.client.download_media(item.media)
        await event.client.send_file(
            "me",
            path,
            caption=f"**Story {story_id}**\n{(item.caption or '').strip()}",
        )
        os.remove(path)
        await status.edit("✅ Story saved to Saved Messages.")
    except Exception as er:
        if "FILE_REFERENCE" in str(er):
            return await status.edit("`Story expired.`")
        await status.edit(f"`Could not download story: {er}`")


# --------------------------------------------------------------------------
# Stars gifts
# --------------------------------------------------------------------------


def _gift_name(gift):
    if getattr(gift, "title", None):
        return gift.title
    return f"Gift {gift.id}"


@ultroid_cmd(pattern="gifts( (.*)|$)")
async def gifts_catalog(event):
    raw = event.pattern_match.group(1).strip().lower()
    try:
        result = await event.client(GetStarGiftsRequest(hash=0))
    except Exception as er:
        return await event.eor(f"`Could not load gifts: {er}`", time=12)
    gifts = list(getattr(result, "gifts", []))
    total = len(gifts)
    if raw == "limited":
        gifts = [x for x in gifts if getattr(x, "limited", False)]
    if not gifts:
        return await event.eor("`No gifts found.`", time=10)
    # Limited gifts first, then cheapest.
    gifts.sort(
        key=lambda g: (
            not getattr(g, "sold_out", False),
            not getattr(g, "limited", False),
            getattr(g, "stars", 0),
        )
    )
    lines = []
    for gift in gifts[:40]:
        title = _gift_name(gift)
        line = f"⭐ `{gift.stars}`  {title}"
        if getattr(gift, "limited", False):
            remains = getattr(gift, "availability_remains", None)
            line += f"  ({remains if remains is not None else '?'} left)"
        if getattr(gift, "sold_out", False):
            line += "  (sold out)"
        if getattr(gift, "require_premium", False):
            line += "  (Premium)"
        lines.append(line)
    title = "Limited Gifts" if raw == "limited" else "Telegram Gifts"
    text = (
        f"**{title}** ({len(gifts)} of {total})\n\n"
        + "\n".join(lines)
        + "\n\nSend gifts in the Telegram app; `.gifts limited` shows limited ones."
    )
    await event.eor(text, time=60)


@ultroid_cmd(pattern="mygifts$")
async def my_gifts(event):
    me = await event.client.get_input_entity("me")
    try:
        result = await event.client(
            GetSavedStarGiftsRequest(peer=me, offset="", limit=30)
        )
    except Exception as er:
        return await event.eor(f"`Could not load your gifts: {er}`", time=12)
    gifts = list(getattr(result, "gifts", []))
    count = getattr(result, "count", len(gifts))
    if not gifts:
        return await event.eor(
            f"**Your Gifts** ({count})\n\nNo gifts yet.", time=30
        )
    lines = []
    for gift in gifts[:30]:
        name = getattr(gift, "name", None) or getattr(gift, "title", None)
        line = f"🎁 {name or 'Gift'}"
        date = getattr(gift, "date", None)
        if date:
            line += f"  `{date.strftime('%Y-%m-%d')}`"
        lines.append(line)
    text = f"**Your Gifts** ({count})\n\n" + "\n".join(lines)
    await event.eor(text, time=60)


@ultroid_cmd(pattern="stars$")
async def stars_cmd(event):
    me = await event.client.get_input_entity("me")
    lines = ["⭐ **Telegram Economy**", ""]
    try:
        result = await event.client(GetStarsStatusRequest(peer=me))
        balance = result.balance
        amount = getattr(balance, "amount", 0)
        nanos = getattr(balance, "nanos", 0) or 0
        lines.append(f"Stars: `{amount + (nanos / 1_000_000_000):g}` ⭐")
    except Exception as er:
        lines.append(f"Stars: `unavailable ({er})`")
    try:
        result = await event.client(GetStarsStatusRequest(peer=me, ton=True))
        balance = result.balance
        raw_amount = getattr(balance, "amount", 0)
        lines.append(f"TON: `{raw_amount / 1_000_000_000:.4f}` 💎")
    except Exception as er:
        lines.append(f"TON: `unavailable ({er})`")
    await event.eor("\n".join(lines), time=30)


# --------------------------------------------------------------------------
# Premium-only: to-do lists and quick replies
# --------------------------------------------------------------------------


def _premium_hint(event):
    return event.eor(
        "`This feature needs Telegram Premium on the account.`", time=10
    )


@ultroid_cmd(pattern="todo( (.*)|$)")
async def make_todo(event):
    """Create a native checklist (Premium)."""
    raw = event.pattern_match.group(1).strip()
    if not raw:
        return await event.eor(
            "**Usage:** `.todo <title> ; item ; item`\n"
            "Requires Telegram Premium.",
            time=10,
        )
    title, *items = [x.strip() for x in raw.split(";") if x.strip()]
    if not items:
        return await event.eor("`Add at least one item after ';'.`", time=10)
    todo = TodoList(
        title=TextWithEntities(title, []),
        list=[
            TodoItem(index + 1, TextWithEntities(item, []))
            for index, item in enumerate(items)
        ],
        others_can_append=True,
        others_can_complete=True,
    )
    try:
        peer = await event.client.get_input_entity(event.chat_id)
        await event.client(
            SendMediaRequest(
                peer=peer,
                media=InputMediaTodo(todo),
                message="",
                random_id=int.from_bytes(os.urandom(8), "big", signed=True),
            )
        )
    except Exception as er:
        if "PREMIUM" in str(er).upper():
            return await _premium_hint(event)
        return await event.eor(f"`Could not create list: {er}`", time=12)
    await _safe_delete(event)
