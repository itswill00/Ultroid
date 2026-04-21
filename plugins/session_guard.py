# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

from . import get_help

__doc__ = get_help("session_guard")

"""
» Commands Available -

• `{i}sessions`
    List all active Telegram sessions on your account.

• `{i}revoke <number>`
    Revoke a session by its number from the `.sessions` list.

• `{i}revokeall`
    Revoke all active sessions except the current one.

• `{i}sessionguard on|off`
    Enable/disable new login monitoring.
    When active, sends an alert to LOG_CHANNEL on any new login detected.
"""

import asyncio
from datetime import datetime

from telethon.tl.functions.account import (
    GetAuthorizationsRequest,
    ResetAuthorizationRequest,
)

try:
    from telethon.tl.functions.account import ResetAuthorizationsRequest
except ImportError:
    # Telethon rename/move fallback
    from telethon.tl.functions.auth import ResetAuthorizationsRequest

from . import LOGS, udB, ultroid_bot, ultroid_cmd

help_session_guard = __doc__

_GUARD_KEY = "SESSION_GUARD"
_KNOWN_HASHES_KEY = "SESSION_KNOWN_HASHES"
_guard_task: asyncio.Task | None = None
_CHECK_INTERVAL = 300  # seconds (5 minutes)


def _fmt_session(auth) -> str:
    country = getattr(auth, "country", "?")
    region = getattr(auth, "region", "")
    platform = getattr(auth, "platform", "?")
    device = getattr(auth, "device_model", "?")
    app = getattr(auth, "app_name", "?")
    date_active = getattr(auth, "date_active", None)
    date_str = date_active.strftime("%d %b %Y %H:%M") if date_active else "?"
    current = "✅ **Current |**" if getattr(auth, "current", False) else ""
    return (
        f"{current}\n"
        f"  Device:  `{device} ({platform})`\n"
        f"  App:     `{app}`\n"
        f"  Region:  `{region}, {country}`\n"
        f"  Active:  `{date_str}`\n"
        f"  Hash:    `{auth.hash}`"
    )


@ultroid_cmd(pattern="sessions$", owner_only=True)
async def list_sessions(e):
    xx = await e.eor("`Session | Fetching active sessions...`")
    try:
        result = await e.client(GetAuthorizationsRequest())
        auths = result.authorizations
    except Exception as err:
        LOGS.exception(err)
        return await xx.edit(f"`Session | Failed: {err}`")

    if not auths:
        return await xx.edit("`Session | No active sessions found.`")

    lines = [f"**Active Sessions ({len(auths)}):**\n"]
    for i, auth in enumerate(auths, 1):
        lines.append(f"**[{i}]** {_fmt_session(auth)}\n")

    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "\n...(truncated)"
    await xx.edit(text)


@ultroid_cmd(pattern="revoke( (.*)|$)", owner_only=True)
async def revoke_session(e):
    match = e.pattern_match.group(1).strip()
    if not match or not match.isdigit():
        return await e.eor("`Session | Example: .revoke 2`\nUse .sessions to see the list.")

    idx = int(match) - 1
    xx = await e.eor("`Session | Fetching session list...`")
    try:
        result = await e.client(GetAuthorizationsRequest())
        auths = result.authorizations
    except Exception as err:
        return await xx.edit(f"`Session | Failed to fetch sessions: {err}`")

    if idx < 0 or idx >= len(auths):
        return await xx.edit(f"`Session | Invalid session number. Choose 1-{len(auths)}.`")

    auth = auths[idx]
    if getattr(auth, "current", False):
        return await xx.edit("`Session | Cannot revoke the currently active session.`")

    try:
        await e.client(ResetAuthorizationRequest(hash=auth.hash))
        await xx.edit(
            f"`Session | Session #{match} revoked successfully.`\n"
            f"Device: `{auth.device_model}`"
        )
    except Exception as err:
        LOGS.exception(err)
        await xx.edit(f"`Session | Failed to revoke session: {err}`")


@ultroid_cmd(pattern="revokeall$", owner_only=True)
async def revoke_all_sessions(e):
    xx = await e.eor("`Session | Revoking all other sessions...`")
    try:
        await e.client(ResetAuthorizationsRequest())
        await xx.edit("`Session | All sessions except the current one have been revoked.`")
    except Exception as err:
        LOGS.exception(err)
        await xx.edit(f"`Session | Failed: {err}`")


@ultroid_cmd(pattern="sessionguard( (.*)|$)", owner_only=True)
async def session_guard(e):
    global _guard_task
    action = e.pattern_match.group(1).strip().lower()
    log_ch = udB.get_key("LOG_CHANNEL")

    if action == "on":
        if not log_ch:
            return await e.eor("`Guard | LOG_CHANNEL is not set.`")

        if _guard_task and not _guard_task.done():
            return await e.eor("`Guard | Session Guard is already active.`")

        udB.set_key(_GUARD_KEY, "on")

        # Snapshot current sessions
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
                        # New login detected
                        for auth in result.authorizations:
                            if str(auth.hash) in new_sessions:
                                alert = (
                                    f"⚠️ **SESSION GUARD — New Login Detected**\n\n"
                                    f"{_fmt_session(auth)}\n\n"
                                    f"`{datetime.now().strftime('%d %b %Y %H:%M:%S')}`"
                                )
                                await ultroid_bot.send_message(log_ch, alert)
                        udB.set_key(_KNOWN_HASHES_KEY, str(current_hashes))
                except Exception as err:
                    LOGS.warning(f"[SESSION GUARD] Error: {err}")

        _guard_task = asyncio.get_event_loop().create_task(_guard_loop())
        await e.eor(
            f"`Guard | Session Guard enabled.`\n"
            f"Interval: `{_CHECK_INTERVAL}s` · Alerts sent to LOG_CHANNEL."
        )

    elif action == "off":
        udB.set_key(_GUARD_KEY, "off")
        if _guard_task and not _guard_task.done():
            _guard_task.cancel()
            _guard_task = None
        await e.eor("`Guard | Session Guard disabled.`")

    else:
        status = udB.get_key(_GUARD_KEY) or "off"
        is_running = bool(_guard_task and not _guard_task.done())
        await e.eor(
            f"**Session Guard**\n"
            f"Status: `{status}` · Running: `{is_running}`\n\n"
            f"Usage: `.sessionguard on` or `.sessionguard off`"
        )
