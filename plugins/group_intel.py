
from . import get_help

__doc__ = get_help("group_intel")

"""
Group Intel — Admin Surveillance Plugin
Monitor group events and forward alerts to LOG_CHANNEL.

Commands:
  .monitor add       — add current group to watchlist
  .monitor remove    — remove current group from watchlist
  .monitor list      — show all monitored groups
  .monitor pause     — pause all monitoring
  .monitor resume    — resume monitoring
  .monitor report    — activity summary (last 24h) for current group
  .setwatch <type> <on|off>
      types: join, leave, ban, promote, link, flood, forward, settings
"""

import asyncio
import time
from collections import defaultdict
from datetime import datetime, timezone

from telethon import events
from telethon.tl import types

from pyUltroid.dB.gban_mute_db import is_gbanned

from . import (
    LOG_CHANNEL,
    LOGS,
    udB,
    ultroid_bot,
    ultroid_cmd,
)

# ── State ──────────────────────────────────────────────────────────────────

# Rate limiter: {(group_id, user_id, event_type): last_log_timestamp}
_rate_cache: dict = {}
RATE_LIMIT_SECS = 1800  # 30 minutes per user per event per group

# Join batcher: {group_id: [(user_id, timestamp), ...]}
_join_buffer: dict = defaultdict(list)
JOIN_BATCH_WINDOW = 120   # seconds
JOIN_BATCH_MIN    = 4     # min joins in window to batch

# Flood tracker: {(group_id, user_id): [timestamps]}
_flood_tracker: dict = defaultdict(list)
FLOOD_COUNT = 5   # messages
FLOOD_SECS  = 10  # within this many seconds

# User info cache: {user_id: (Entity, fetched_at)}
_user_cache: dict = {}
USER_CACHE_TTL = 3600  # 1 hour

# Admin cache: {group_id: (set(admin_ids), fetched_at)}
_admin_cache: dict = {}
ADMIN_CACHE_TTL = 1800  # 30 minutes

# Activity counter for .monitor report: {group_id: {event_type: count}}
_activity: dict = defaultdict(lambda: defaultdict(int))
_activity_reset: dict = {}   # group_id: timestamp of last reset

# ── DB Helpers ─────────────────────────────────────────────────────────────

DB_KEY_GROUPS   = "INTEL_GROUPS"    # dict: {group_id: group_title}
DB_KEY_PAUSED   = "INTEL_PAUSED"    # bool
DB_KEY_FLAGS    = "INTEL_FLAGS"     # dict: {event_type: bool}

DEFAULT_FLAGS = {
    "join":     True,
    "leave":    False,   # too noisy by default
    "ban":      True,
    "promote":  True,
    "link":     True,
    "flood":    True,
    "forward":  True,
    "settings": True,
}


def _get_groups() -> dict:
    return udB.get_key(DB_KEY_GROUPS) or {}


def _save_groups(g: dict):
    udB.set_key(DB_KEY_GROUPS, g)


def _get_flags() -> dict:
    stored = udB.get_key(DB_KEY_FLAGS) or {}
    return {**DEFAULT_FLAGS, **stored}


def _is_paused() -> bool:
    return bool(udB.get_key(DB_KEY_PAUSED))


def _flag_on(event_type: str) -> bool:
    return _get_flags().get(event_type, True)


# ── Admin Helper ────────────────────────────────────────────────────────────

async def _get_admins(chat_id: int) -> set:
    """Fetch and cache admins for a group."""
    now = time.time()
    if chat_id in _admin_cache:
        admins, fetched = _admin_cache[chat_id]
        if now - fetched < ADMIN_CACHE_TTL:
            return admins

    try:
        admins = {
            p.id
            for p in await ultroid_bot.get_participants(
                chat_id, filter=types.ChannelParticipantsAdmins
            )
        }
        _admin_cache[chat_id] = (admins, now)
        return admins
    except Exception as e:
        LOGS.debug(f"group_intel: failed to fetch admins for {chat_id} — {e}")
        return set()


async def _is_admin(chat_id: int, user_id: int) -> bool:
    """Check if a user is an admin using cache."""
    admins = await _get_admins(chat_id)
    return user_id in admins


# ── Risk Scoring ───────────────────────────────────────────────────────────

PROMO_KEYWORDS = [
    "promo", "jual", "murah", "diskon", "sale", "buy", "cheap", "bonus", "slot",
    "wa.me", "t.me/+", "http", "discord.gg", "bit.ly", "invest", "crypto",
]


def _risk_score(user, message_text: str = "") -> tuple[int, str, list[str]]:
    """Return (score, label, [reasons]). Score >= 5 = HIGH, 3-4 = MEDIUM, <3 = LOW."""
    score = 0
    reasons = []

    if not user:
        return 0, "LOW", []

    # 1. Native Telegram Flags (CRITICAL)
    if getattr(user, "scam", False):
        score += 5
        reasons.append("TELEGRAM SCAM FLAG")
    if getattr(user, "fake", False):
        score += 4
        reasons.append("TELEGRAM FAKE FLAG")
    if getattr(user, "deleted", False):
        score += 5
        reasons.append("DELETED ACCOUNT")

    # 2. Global Ban Check
    if is_gbanned(user.id):
        score += 6
        reasons.append("GLOBALLY BANNED (GBAN)")

    # 3. Account Age (Refined)
    if hasattr(user, "id"):
        uid = user.id
        # Rough estimates for 2024: IDs > 7.3B are very new
        if uid > 7_300_000_000:
            score += 3
            reasons.append("brand new account (2024+)")
        elif uid > 6_000_000_000:
            score += 2
            reasons.append("relatively new account")
        elif uid > 4_000_000_000:
            score += 1
            reasons.append("moderate account age")

    # 4. Profile Completeness
    if not getattr(user, "photo", None):
        score += 2
        reasons.append("no profile photo")
    if not getattr(user, "username", None):
        score += 1
        reasons.append("no username")
    if getattr(user, "premium", False):
        score -= 2  # Premium users are less likely to be bots
        reasons.append("verified premium user")

    # 5. Bio / First Name keywords
    bio = ""
    if getattr(user, "first_name", None):
        bio += user.first_name.lower()
    if getattr(user, "last_name", None):
        bio += " " + user.last_name.lower()
    if getattr(user, "about", None):
        bio += " " + user.about.lower()

    for kw in PROMO_KEYWORDS:
        if kw in bio:
            score += 2
            reasons.append(f"promo keyword in profile: '{kw}'")
            break

    # 6. Message Content
    if message_text:
        text_lower = message_text.lower()
        if any(kw in text_lower for kw in PROMO_KEYWORDS):
            score += 2
            reasons.append("suspicious keywords in message")

        link_count = text_lower.count("http") + text_lower.count("t.me")
        if link_count >= 2:
            score += 3
            reasons.append(f"multiple links ({link_count})")
        elif link_count == 1:
            score += 1
            reasons.append("contains link")

    # Final Labeling
    score = max(0, score)  # Ensure no negative
    label = "HIGH" if score >= 6 else "MEDIUM" if score >= 3 else "LOW"
    return score, label, reasons


# = Security Monitor Logic =

async def _send_alert(
    event_type: str,
    group_id: int,
    group_title: str,
    body: str,
    risk_label: str = "",
    user_id: int = None,
):
    """Send a formatted Double-Box alert to LOG_CHANNEL. Rate-limited."""
    if not LOG_CHANNEL or _is_paused() or not _flag_on(event_type):
        return

    # Track activity
    _activity[group_id][event_type] += 1
    if group_id not in _activity_reset:
        _activity_reset[group_id] = time.time()

    # Rate-limit check
    rate_key = (group_id, user_id, event_type) if user_id else (group_id, event_type)
    now = time.time()
    if _rate_cache.get(rate_key, 0) + RATE_LIMIT_SECS > now:
        return
    _rate_cache[rate_key] = now

    ts = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")

    # Aesthetic Minimalist Header
    text = (
        f"🛡️ **Intel Alert: {event_type.title()}**\n\n"
        f"📍 **Group:** {group_title}\n"
        f"{body.strip()}"
    )
    if risk_label:
        text += f"\n🚨 **Risk:** {risk_label}"

    text += f"\n\n⏱️ `{ts}`"

    try:
        await ultroid_bot.send_message(LOG_CHANNEL, text)
    except Exception as e:
        LOGS.warning(f"group_intel: failed to send alert — {e}")


# Legacy helper for compatibility during refactor
async def _send_alert_per_user(event_type, group_id, group_title, user_id, body, risk_label=""):
    await _send_alert(event_type, group_id, group_title, body, risk_label, user_id)


# = User Info Helper =

async def _get_user(user_id: int):
    """Cached user entity fetch."""
    now = time.time()
    if user_id in _user_cache:
        entity, fetched = _user_cache[user_id]
        if now - fetched < USER_CACHE_TTL:
            return entity

    try:
        entity = await ultroid_bot.get_entity(user_id)
        _user_cache[user_id] = (entity, now)
        return entity
    except Exception:
        return None


def _format_user(user) -> str:
    if not user:
        return "Unknown"
    name = (getattr(user, "first_name", "") or "User")[:20]
    return f"{name} `[{user.id}]`"


# = Join Batcher =

async def _handle_join_batch(group_id: int, group_title: str):
    """Waits JOIN_BATCH_WINDOW seconds then sends a batched join report if needed."""
    await asyncio.sleep(JOIN_BATCH_WINDOW)
    entries = _join_buffer.pop(group_id, [])
    if len(entries) < JOIN_BATCH_MIN:
        return  # already sent individually or too few

    # Batch report
    ids_preview = ", ".join(f"`{uid}`" for uid, _ in entries[:3])
    if len(entries) > 3:
        ids_preview += "..."

    body = (
        f"👥 **Count:** {len(entries)} joins\n"
        f"⏳ **Window:** {JOIN_BATCH_WINDOW}s\n"
        f"👤 **Users:** {ids_preview}"
    )

    _rate_cache.pop((group_id, "join"), None)
    await _send_alert("join", group_id, group_title, body, risk_label="MEDIUM — MASS JOIN")


# = Event Handlers =

@ultroid_bot.on(events.ChatAction())
async def _intel_chat_action(event):
    groups = _get_groups()
    chat_id = event.chat_id

    if str(chat_id) not in groups and chat_id not in groups:
        return

    group_title = groups.get(str(chat_id)) or groups.get(chat_id, str(chat_id))

    # ── Member joined ──────────────────────────────────────────
    if event.user_joined or event.user_added:
        if not _flag_on("join"):
            return

        user = await _get_user(event.user_id)
        if not user:
            # Fallback if user entity is not resolvable
            LOGS.warning(f"GroupIntel | Could not resolve user {event.user_id} in {chat_id}")
            return

        _, risk_label, risk_reasons = _risk_score(user)

        buf = _join_buffer[chat_id]
        buf.append((event.user_id, time.time()))

        if len(buf) == 1:
            asyncio.create_task(_handle_join_batch(chat_id, group_title))

        if len(buf) < JOIN_BATCH_MIN:
            action = getattr(event, "action", None)
            via = "link" if isinstance(action, types.MessageActionChatJoinedByLink) else "added"
            body = (
                f"👤 **User:** {_format_user(user)}\n"
                f"🔗 **Via:** {via}"
            )
            # Add risk flags if any
            score, risk_label, risk_reasons = _risk_score(user)
            if risk_reasons:
                flags = ", ".join(risk_reasons)
                body += f"\n🚩 **Flags:** {flags}"

            await _send_alert("join", event.chat_id, group_title, body, risk_label, user.id)

    # ── Member left / kicked / banned ─────────────────────────
    elif event.user_left or event.user_kicked:
        action_type = "kicked" if event.user_kicked else "left"
        if not _flag_on("ban" if event.user_kicked else "leave"):
            return

        user = await _get_user(event.user_id)
        if not user:
            # Fallback if user entity is not resolvable
            LOGS.warning(f"GroupIntel | Left event for unresolvable user {event.user_id}")
            return

        actor_id = event.action_message.sender_id if event.action_message else None

        body = (
            f"👤 **User:** {_format_user(user)}\n"
            f"🚫 **Action:** {action_type}"
        )
        if actor_id and actor_id != event.user_id:
            actor = await _get_user(actor_id)
            body += f"\n👮 **By:** {_format_user(actor)}"

        await _send_alert(
            "ban" if event.user_kicked else "leave",
            chat_id, group_title, body, user_id=event.user_id
        )

    # ── Settings / Admin change ──────────────────────────────
    if event.new_title or event.new_photo is not None:
        if not _flag_on("settings"):
            return
        what = "title" if event.new_title else "photo"
        actor_id = event.action_message.sender_id if event.action_message else None
        actor = await _get_user(actor_id) if actor_id else None
        body = (
            f"📝 **Change:** {what}\n"
            f"👤 **By:** {_format_user(actor)}"
        )
        await _send_alert("settings", chat_id, group_title, body)

    if hasattr(event, "action") and isinstance(event.action, types.MessageActionChatEditAdmin):
        if not _flag_on("promote"):
            return
        user = await _get_user(event.user_id)
        actor_id = event.action_message.sender_id if event.action_message else None
        actor = await _get_user(actor_id) if actor_id else None
        demoted = getattr(event.action, "admin_rights", None) is None
        action_str = "demoted" if demoted else "promoted"
        body = (
            f"👤 **User:** {_format_user(user)}\n"
            f"⚡ **Action:** {action_str}\n"
            f"👮 **By:** {_format_user(actor)}"
        )
        await _send_alert("promote", chat_id, group_title, body, user_id=event.user_id)


@ultroid_bot.on(events.NewMessage(incoming=True))
async def _intel_new_message(event):
    if not event.is_group:
        return

    groups = _get_groups()
    chat_id = event.chat_id

    if str(chat_id) not in groups and chat_id not in groups:
        return

    group_title = groups.get(str(chat_id)) or groups.get(chat_id, str(chat_id))

    sender = await event.get_sender()
    if not sender:
        return

    # Skip messages from group admins (using cache for efficiency)
    if await _is_admin(chat_id, sender.id):
        return

    text = event.raw_text or ""

    # ── Flood detection ──────────────────────────────────────
    if _flag_on("flood"):
        now = time.time()
        key = (chat_id, sender.id)
        timestamps = _flood_tracker[key]
        timestamps.append(now)
        # Keep only recent
        _flood_tracker[key] = [t for t in timestamps if now - t <= FLOOD_SECS]

        if len(_flood_tracker[key]) >= FLOOD_COUNT:
            body = (
                f"👤 **User:** {_format_user(sender)}\n"
                f"📊 **Rate:** {len(_flood_tracker[key])} msgs / {FLOOD_SECS}s"
            )
            _flood_tracker[key] = []
            await _send_alert("flood", chat_id, group_title, body, risk_label="HIGH — FLOOD", user_id=sender.id)

    # ── Link detection ───────────────────────────────────────
    if _flag_on("link"):
        has_link = (
            "http" in text.lower()
            or "t.me/" in text.lower()
            or bool(event.entities and any(
                isinstance(e, (
                    types.MessageEntityUrl,
                    types.MessageEntityTextUrl,
                ))
                for e in event.entities
            ))
        )
        if has_link:
            _, risk_label, risk_reasons = _risk_score(sender, text)
            msg_snip = text[:40].replace('\n', ' ')[:25]
            body = (
                f"👤 **User:** {_format_user(sender)}\n"
                f"💬 **Msg:** {msg_snip}..."
            )
            if risk_reasons:
                flags = ", ".join(risk_reasons[:2])
                body += f"\n🚩 **Flags:** {flags}"
            await _send_alert("link", chat_id, group_title, body, risk_label, sender.id)

    # ── Forward detection ────────────────────────────────────
    if _flag_on("forward") and event.forward:
        fwd = event.forward
        origin = "unknown"
        if fwd.chat:
            origin = f"@{fwd.chat.username}" if getattr(fwd.chat, "username", None) else str(fwd.chat_id)
        elif fwd.sender:
            origin = f"@{fwd.sender.username}" if getattr(fwd.sender, "username", None) else str(fwd.from_id)

        body = (
            f"👤 **User:** {_format_user(sender)}\n"
            f"📤 **From:** {origin}"
        )
        await _send_alert("forward", chat_id, group_title, body, user_id=sender.id)


# = Commands =

@ultroid_cmd(pattern=r"monitor(?: (.+))?$")
async def _monitor_cmd(ult):
    args = (ult.pattern_match.group(1) or "").strip().split()
    action = args[0].lower() if args else "list"

    # ── monitor add ──────────────────────────────────────────
    if action == "add":
        if not ult.is_group:
            return await ult.eor("`Use this command inside the group you want to monitor.`")
        chat   = await ult.get_chat()
        gid    = str(ult.chat_id)
        gtitle = getattr(chat, "title", str(ult.chat_id))
        groups = _get_groups()
        if gid in groups:
            return await ult.eor(f"`{gtitle}` is already being monitored.")
        groups[gid] = gtitle
        _save_groups(groups)
        return await ult.eor(
            f"✅ **Intel — Monitoring Enabled**\n"
            f"---"
            f"\n📍 **Group:** {gtitle}"
            f"\n🆔 **ID:** `{gid}`"
        )

    # Monitor Remove
    elif action == "remove":
        if not ult.is_group:
            return await ult.eor("`Use this inside the target group.`")
        gid    = str(ult.chat_id)
        groups = _get_groups()
        if gid not in groups:
            return await ult.eor("`This group is not in the watchlist.`")
        title = groups.pop(gid)
        _save_groups(groups)
        return await ult.eor(f"❌ **Intel — Monitoring Removed**\n📍 **Group:** {title}")

    # Monitor List
    elif action == "list":
        groups = _get_groups()
        if not groups:
            return await ult.eor("`No groups in watchlist. Use .monitor add inside a group.`")
        lines = "📋 **Intel — Watchlist**\n---\n"
        for gid, title in groups.items():
            lines += f"• `{title}` — `{gid}`\n"
        flags = _get_flags()
        enabled = [k for k, v in flags.items() if v]
        lines += f"\n🚩 **Flags:** {', '.join(enabled)}"
        lines += f"\n📊 **Status:** {'⏸ PAUSED' if _is_paused() else '▶️ ACTIVE'}"
        return await ult.eor(lines)

    # ── monitor pause / resume ────────────────────────────────
    elif action == "pause":
        udB.set_key(DB_KEY_PAUSED, True)
        return await ult.eor("`INTEL — Monitoring paused.`")

    elif action == "resume":
        udB.del_key(DB_KEY_PAUSED)
        return await ult.eor("`INTEL — Monitoring resumed.`")

    elif action == "report":
        chat_id = str(ult.chat_id) if ult.is_group else None
        if not chat_id or chat_id not in _get_groups():
            return await ult.eor("`Use this inside a monitored group.`")

        data = _activity.get(int(chat_id), {})
        reset = _activity_reset.get(int(chat_id), time.time())
        delta = int(time.time() - reset)
        period = f"{delta // 3600}h {(delta % 3600) // 60}m"

        if not data:
            return await ult.eor("`No activity recorded.`")

        chat = await ult.get_chat()
        lines = (
            f"📊 **Activity Report**\n"
            f"📍 **Group:** {chat.title}\n"
            f"🕒 **Period:** {period}\n"
            f"---"
        )
        for ev, count in sorted(data.items(), key=lambda x: -x[1]):
            lines += f"\n• **{ev.title()}:** {count}"
        return await ult.eor(lines)

    else:
        return await ult.eor(
            "`Usage:`\n"
            "`.monitor add` — add this group\n"
            "`.monitor remove` — remove this group\n"
            "`.monitor list` — show watchlist\n"
            "`.monitor pause/resume` — toggle\n"
            "`.monitor report` — 24h stats"
        )


@ultroid_cmd(pattern=r"setwatch (\w+) (on|off)$")
async def _setwatch_cmd(ult):
    args    = ult.pattern_match.groups()
    flag    = args[0].lower()
    value   = args[1].lower() == "on"

    valid = list(DEFAULT_FLAGS.keys())
    if flag not in valid:
        return await ult.eor(
            f"`Invalid type.`\nValid: `{', '.join(valid)}`"
        )

    flags = _get_flags()
    flags[flag] = value
    udB.set_key(DB_KEY_FLAGS, flags)
    state = "enabled" if value else "disabled"
    await ult.eor(f"`INTEL — {flag} monitoring {state}`")
