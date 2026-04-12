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
from telethon.tl.functions.channels import GetParticipantRequest

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


# ── Risk Scoring ───────────────────────────────────────────────────────────

PROMO_KEYWORDS = [
    "promo", "jual", "murah", "diskon", "sale", "buy", "cheap",
    "wa.me", "t.me/+", "http", "discord.gg", "bit.ly",
]


def _risk_score(user, message_text: str = "") -> tuple[int, list[str]]:
    """Return (score, [reasons]). Score >= 5 = HIGH, 3-4 = MEDIUM, <3 = LOW."""
    score = 0
    reasons = []

    # Account age (from user.id Snowflake — rough estimate)
    # Real account age requires extra API call; use ID range as proxy
    if user and hasattr(user, "id"):
        uid = user.id
        # Accounts registered after ~2021 have ID > 1_500_000_000
        if uid > 6_000_000_000:
            score += 3
            reasons.append("very new account")
        elif uid > 4_000_000_000:
            score += 1
            reasons.append("relatively new account")

    # Bio / first name check
    bio = ""
    if user and hasattr(user, "first_name") and user.first_name:
        bio += user.first_name.lower()
    if hasattr(user, "about") and user.about:
        bio += " " + user.about.lower()

    for kw in PROMO_KEYWORDS:
        if kw in bio:
            score += 2
            reasons.append(f"promo keyword in profile: '{kw}'")
            break  # only count once for bio

    # Message text
    if message_text:
        text_lower = message_text.lower()
        link_count = text_lower.count("http") + text_lower.count("t.me")
        if link_count >= 2:
            score += 3
            reasons.append(f"{link_count} links in message")
        elif link_count == 1:
            score += 2
            reasons.append("link in message")
        for kw in PROMO_KEYWORDS[:6]:
            if kw in text_lower:
                score += 1
                reasons.append(f"promo keyword in message: '{kw}'")
                break

    label = "HIGH" if score >= 5 else "MEDIUM" if score >= 3 else "LOW"
    return score, label, reasons


# ── Alert Sender ───────────────────────────────────────────────────────────

async def _send_alert(event_type: str, group_id: int, group_title: str, body: str, risk_label: str = ""):
    """Send a formatted alert to LOG_CHANNEL. Rate-limited."""
    if not LOG_CHANNEL:
        return
    if _is_paused():
        return
    if not _flag_on(event_type):
        return

    # Track activity for .monitor report
    _activity[group_id][event_type] += 1
    if group_id not in _activity_reset:
        _activity_reset[group_id] = time.time()

    # Rate-limit check (keyed on group + event type only for group-wide events)
    rate_key = (group_id, event_type)
    now = time.time()
    if _rate_cache.get(rate_key, 0) + RATE_LIMIT_SECS > now:
        return
    _rate_cache[rate_key] = now

    risk_line = f"\n`risk    {risk_label}`" if risk_label else ""
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")

    text = (
        f"`GROUP INTEL ──────────────────`\n"
        f"`group   {group_title}`\n"
        f"`event   {event_type}`\n"
        f"`──────────────────────────────`\n"
        f"{body}"
        f"{risk_line}\n"
        f"`──────────────────────────────`\n"
        f"`{ts}`"
    )

    try:
        await ultroid_bot.send_message(LOG_CHANNEL, text)
    except Exception as e:
        LOGS.warning(f"group_intel: failed to send alert — {e}")


async def _send_alert_per_user(
    event_type: str,
    group_id: int,
    group_title: str,
    user_id: int,
    body: str,
    risk_label: str = "",
):
    """Like _send_alert but rate-limited per (group, user, event_type)."""
    if not LOG_CHANNEL:
        return
    if _is_paused():
        return
    if not _flag_on(event_type):
        return

    _activity[group_id][event_type] += 1
    if group_id not in _activity_reset:
        _activity_reset[group_id] = time.time()

    rate_key = (group_id, user_id, event_type)
    now = time.time()
    if _rate_cache.get(rate_key, 0) + RATE_LIMIT_SECS > now:
        return
    _rate_cache[rate_key] = now

    risk_line = f"\n`risk    {risk_label}`" if risk_label else ""
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")

    text = (
        f"`GROUP INTEL ──────────────────`\n"
        f"`group   {group_title}`\n"
        f"`event   {event_type}`\n"
        f"`──────────────────────────────`\n"
        f"{body}"
        f"{risk_line}\n"
        f"`──────────────────────────────`\n"
        f"`{ts}`"
    )

    try:
        await ultroid_bot.send_message(LOG_CHANNEL, text)
    except Exception as e:
        LOGS.warning(f"group_intel: failed to send alert — {e}")


# ── User Info Helper ────────────────────────────────────────────────────────

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
        return "`unknown`"
    name = getattr(user, "first_name", "") or ""
    if getattr(user, "last_name", None):
        name += f" {user.last_name}"
    uname = f"@{user.username}" if getattr(user, "username", None) else "no username"
    return f"`{name}` ({uname} · `{user.id}`)"


# ── Join Batcher ────────────────────────────────────────────────────────────

async def _handle_join_batch(group_id: int, group_title: str):
    """Waits JOIN_BATCH_WINDOW seconds then sends a batched join report if needed."""
    await asyncio.sleep(JOIN_BATCH_WINDOW)
    entries = _join_buffer.pop(group_id, [])
    if len(entries) < JOIN_BATCH_MIN:
        return  # already sent individually or too few

    # Batch report
    body = f"`count   {len(entries)} joins in {JOIN_BATCH_WINDOW}s`\n"
    ids_preview = ", ".join(str(uid) for uid, _ in entries[:5])
    if len(entries) > 5:
        ids_preview += f" … +{len(entries) - 5} more"
    body += f"`users   {ids_preview}`\n"

    _rate_cache.pop((group_id, "join"), None)   # clear rate limit so batch goes through
    await _send_alert("join", group_id, group_title, body, risk_label="MEDIUM — mass join")


# ── Event Handlers ─────────────────────────────────────────────────────────

@ultroid_bot.on(events.ChatAction())
async def _intel_chat_action(event):
    groups = _get_groups()
    chat_id = event.chat_id

    # Only process if this group is in our watchlist
    if str(chat_id) not in groups and chat_id not in groups:
        return

    group_title = groups.get(str(chat_id)) or groups.get(chat_id, str(chat_id))

    # ── Member joined ──────────────────────────────────────────
    if event.user_joined or event.user_added:
        if not _flag_on("join"):
            return

        user = await _get_user(event.user_id)
        _, risk_label, risk_reasons = _risk_score(user)

        # Batch logic: buffer joins; if count < MIN send individually
        buf = _join_buffer[chat_id]
        buf.append((event.user_id, time.time()))

        if len(buf) == 1:
            # First join in window — schedule batch check
            asyncio.get_event_loop().create_task(
                _handle_join_batch(chat_id, group_title)
            )

        if len(buf) < JOIN_BATCH_MIN:
            # Send individually until batch threshold
            via = "via link" if event.user_joined else "added by admin"
            body = (
                f"`user    {_format_user(user)}`\n"
                f"`via     {via}`\n"
            )
            if risk_reasons:
                body += f"`flags   {', '.join(risk_reasons[:2])}`\n"

            await _send_alert_per_user(
                "join", chat_id, group_title, event.user_id, body, risk_label
            )

    # ── Member left / kicked / banned ─────────────────────────
    elif event.user_left or event.user_kicked:
        action_type = "kicked" if event.user_kicked else "left"
        if not _flag_on("ban" if event.user_kicked else "leave"):
            return

        user    = await _get_user(event.user_id)
        actor   = await _get_user(event.action_message.sender_id) if event.action_message else None

        body = (
            f"`user    {_format_user(user)}`\n"
            f"`action  {action_type}`\n"
        )
        if actor and actor.id != event.user_id:
            body += f"`by      {_format_user(actor)}`\n"

        await _send_alert_per_user(
            "ban" if event.user_kicked else "leave",
            chat_id, group_title, event.user_id, body
        )

    # ── Admin promotion / demotion ─────────────────────────────
    elif isinstance(event.action, (
        types.MessageActionChatEditAdmin,
        types.MessageActionChatAddUser,
    )) or event.new_title or event.new_photo is not None:

        # Group settings change
        if event.new_title or event.new_photo is not None:
            if not _flag_on("settings"):
                return
            what = "title changed" if event.new_title else "photo changed"
            new_val = f" → `{event.new_title}`" if event.new_title else ""
            actor = await _get_user(event.action_message.sender_id) if event.action_message else None
            body = (
                f"`change  {what}{new_val}`\n"
                f"`by      {_format_user(actor)}`\n"
            )
            await _send_alert("settings", chat_id, group_title, body)

    # Telethon emits admin changes as ChatParticipantAdmin
    if hasattr(event, "action") and isinstance(
        event.action, types.MessageActionChatEditAdmin
    ):
        if not _flag_on("promote"):
            return
        user  = await _get_user(event.user_id)
        actor = await _get_user(event.action_message.sender_id) if event.action_message else None
        demoted = getattr(event.action, "admin_rights", None) is None
        action_str = "demoted" if demoted else "promoted to admin"
        body = (
            f"`user    {_format_user(user)}`\n"
            f"`action  {action_str}`\n"
            f"`by      {_format_user(actor)}`\n"
        )
        await _send_alert_per_user(
            "promote", chat_id, group_title, event.user_id, body
        )


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

    # Skip messages from group admins (we trust them)
    try:
        participant = await ultroid_bot(GetParticipantRequest(chat_id, sender.id))
        is_admin = isinstance(
            participant.participant,
            (types.ChannelParticipantAdmin, types.ChannelParticipantCreator),
        )
        if is_admin:
            return
    except Exception:
        is_admin = False

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
                f"`user    {_format_user(sender)}`\n"
                f"`count   {len(_flood_tracker[key])} messages / {FLOOD_SECS}s`\n"
            )
            _flood_tracker[key] = []   # reset after alert
            await _send_alert_per_user(
                "flood", chat_id, group_title, sender.id, body, "HIGH"
            )

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
            body = (
                f"`user    {_format_user(sender)}`\n"
                f"`msg     {text[:120].replace(chr(96), chr(39))}{'...' if len(text)>120 else ''}`\n"
            )
            if risk_reasons:
                body += f"`flags   {', '.join(risk_reasons[:3])}`\n"
            await _send_alert_per_user(
                "link", chat_id, group_title, sender.id, body, risk_label
            )

    # ── Forward detection ────────────────────────────────────
    if _flag_on("forward") and event.forward:
        fwd = event.forward
        origin = ""
        if fwd.chat:
            origin = f"@{fwd.chat.username}" if getattr(fwd.chat, "username", None) else str(fwd.chat_id)
        elif fwd.sender:
            origin = f"@{fwd.sender.username}" if getattr(fwd.sender, "username", None) else str(fwd.from_id)

        body = (
            f"`user    {_format_user(sender)}`\n"
            f"`from    {origin or 'unknown'}`\n"
            f"`msg     {text[:80].replace(chr(96), chr(39))}{'...' if len(text)>80 else ''}`\n"
        )
        await _send_alert_per_user(
            "forward", chat_id, group_title, sender.id, body
        )


# ── Commands ────────────────────────────────────────────────────────────────

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
            f"`INTEL — Monitoring enabled`\n`group   {gtitle}`\n`id      {gid}`"
        )

    # ── monitor remove ────────────────────────────────────────
    elif action == "remove":
        if not ult.is_group:
            return await ult.eor("`Use this inside the target group.`")
        gid    = str(ult.chat_id)
        groups = _get_groups()
        if gid not in groups:
            return await ult.eor("`This group is not in the watchlist.`")
        title = groups.pop(gid)
        _save_groups(groups)
        return await ult.eor(f"`INTEL — Monitoring removed`\n`group   {title}`")

    # ── monitor list ─────────────────────────────────────────
    elif action == "list":
        groups = _get_groups()
        if not groups:
            return await ult.eor("`No groups in watchlist. Use .monitor add inside a group.`")
        lines = "`INTEL — Watchlist`\n`──────────────────────────────`\n"
        for gid, title in groups.items():
            lines += f"`{title}` — `{gid}`\n"
        flags = _get_flags()
        enabled = [k for k, v in flags.items() if v]
        lines += f"\n`flags   {', '.join(enabled)}`"
        lines += f"\n`status  {'PAUSED' if _is_paused() else 'ACTIVE'}`"
        return await ult.eor(lines)

    # ── monitor pause / resume ────────────────────────────────
    elif action == "pause":
        udB.set_key(DB_KEY_PAUSED, True)
        return await ult.eor("`INTEL — Monitoring paused.`")

    elif action == "resume":
        udB.del_key(DB_KEY_PAUSED)
        return await ult.eor("`INTEL — Monitoring resumed.`")

    # ── monitor report ────────────────────────────────────────
    elif action == "report":
        chat_id = str(ult.chat_id) if ult.is_group else None
        if not chat_id or chat_id not in _get_groups():
            return await ult.eor("`Use this inside a monitored group.`")

        data   = _activity.get(int(chat_id), {})
        reset  = _activity_reset.get(int(chat_id), time.time())
        delta  = int(time.time() - reset)
        hours  = delta // 3600
        mins   = (delta % 3600) // 60

        if not data:
            return await ult.eor("`No activity recorded since last reset.`")

        chat   = await ult.get_chat()
        title  = getattr(chat, "title", chat_id)
        lines  = f"`INTEL REPORT — {title}`\n`period  {hours}h {mins}m`\n`──────────────────────────────`\n"
        for event_type, count in sorted(data.items(), key=lambda x: -x[1]):
            lines += f"`{event_type:<10} {count}`\n"
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
