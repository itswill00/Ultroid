# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/TeamUltroid/pyUltroid/blob/main/LICENSE>.

import inspect
import random
import re
import time
from traceback import format_exc

from telethon import Button
from telethon.errors import QueryIdInvalidError
from telethon.events import CallbackQuery, InlineQuery, NewMessage
from telethon.tl.types import InputWebDocument

from .. import LOGS, asst, udB, ultroid_bot
from ..dB.verify_db import UsageLogs, is_fully_authorized, is_verified
from ..fns.admins import admin_check
from . import append_or_update, owner_and_sudos

OWNER = ultroid_bot.full_name

MSG = f"""
**Ultroid - UserBot**
➖➖➖➖➖➖➖➖➖➖
**Owner**: [{OWNER}](tg://user?id={ultroid_bot.uid})
**Support**: @TeamUltroid
➖➖➖➖➖➖➖➖➖➖
"""

IN_BTTS = [
    [
        Button.url(
            "Repository",
            url="https://github.com/TeamUltroid/Ultroid",
        ),
        Button.url("Support", url="https://t.me/UltroidSupportChat"),
    ]
]


# decorator for assistant


def asst_cmd(pattern=None, load=None, owner=False, public=False, **kwargs):
    """Decorator for assistant's command"""
    name = inspect.stack()[1].filename.split("/")[-1].replace(".py", "")
    kwargs["forwards"] = False

    def ult(func):
        if pattern:
            kwargs["pattern"] = re.compile(f"^/{pattern}")

        async def handler(event):
            sender_id = event.sender_id
            is_owner_or_sudo = sender_id in owner_and_sudos()

            if owner and not is_owner_or_sudo:
                return

            # --- Verification Gateway (Identity & Logic Challenge) ---
            if not is_owner_or_sudo:
                is_command = event.text and event.text.startswith("/")
                # If this is a generic listener (no pattern) and NOT a command,
                # we bypass verification to allow background services (PMBot, Auto-DL) to function.
                if not pattern and not is_command:
                    try:
                        return await func(event)
                    except Exception as er:
                        LOGS.exception(er)
                        return

                # Gate 1: Identity Verify (Click Button)
                if not is_verified(sender_id):
                    auth_text = (
                        f"**User Verification**\n"
                        f"---\n"
                        f"Please verify your identity to use this bot.\n\n"
                        f"ID: `{sender_id}`"
                    )
                    buttons = [[Button.inline("Verify Me", data=f"verify_user|{sender_id}")]]
                    try:
                        return await event.reply(auth_text, buttons=buttons)
                    except Exception:
                        return

                # Gate 2: Public Authorization (Whitelist or Public Flag)
                if not public:
                    return # Block non-public commands for unauth users

                # Gate 3: Logic Challenge (Captcha)
                if not is_fully_authorized(sender_id):
                    a, b = random.randint(1, 9), random.randint(1, 9)
                    ans = a + b
                    # Shuffle options
                    opts = list({ans, ans+1, ans-1, random.randint(2, 18)})
                    random.shuffle(opts)
                    btn_row = [Button.inline(str(o), data=f"captcha|{sender_id}|{o}|{ans}") for o in opts]

                    auth_text = (
                        f"**Captcha Challenge**\n"
                        f"---\n"
                        f"Solve this once to enable public commands:\n\n"
                        f"**Question:** `{a} + {b} = ?`"
                    )
                    return await event.reply(auth_text, buttons=[btn_row])

                # Gate 4: Rate Limiting (10 req/hour)
                now = time.time()
                history = UsageLogs.get().get(str(sender_id), [])
                # Clean old logs (> 1 hour)
                history = [t for t in history if now - t < 3600]
                if len(history) >= 10:
                    return await event.reply("**Rate Limit Exceeded**\n\nPublic users are limited to 10 requests per hour.")
                history.append(now)
                UsageLogs.add({str(sender_id): history})
            # ----------------------------------------

            try:
                await func(event)
            except Exception as er:
                LOGS.exception(er)

        asst.add_event_handler(handler, NewMessage(**kwargs))
        if load is not None:
            append_or_update(load, func, name, kwargs)

        # Hook into Help Engine registry to prevent "Not Valid Plugin" mismatch
        if pattern:
            import inspect
            from pathlib import Path

            from ..dB._core import LIST
            file_stem = Path(inspect.stack()[1].filename).stem
            # Prefix with '/' to distinguish assistant commands
            LIST.setdefault(file_stem, []).append(f"/{pattern}")

    return ult


def callback(data=None, from_users=None, admins=False, owner=False, **kwargs):
    """Assistant's callback decorator"""
    if from_users is None:
        from_users = []
    if "me" in from_users:
        from_users.remove("me")
        from_users.append(ultroid_bot.uid)

    def ultr(func):
        async def wrapper(event):
            if admins and not await admin_check(event):
                return
            if from_users and event.sender_id not in from_users:
                return await event.answer("Not for You!", alert=True)
            if owner and event.sender_id not in owner_and_sudos():
                return await event.answer(f"This is {OWNER}'s bot!!")
            try:
                await func(event)
            except Exception as er:
                from telethon.errors import MessageNotModifiedError
                if isinstance(er, MessageNotModifiedError):
                    return
                LOGS.exception(er)

        asst.add_event_handler(wrapper, CallbackQuery(data=data, **kwargs))

    return ultr


def in_pattern(pattern=None, owner=False, **kwargs):
    """Assistant's inline decorator."""

    def don(func):
        async def wrapper(event):
            if owner and event.sender_id not in owner_and_sudos():
                res = [
                    await event.builder.article(
                        title="Ultroid Userbot",
                        url="https://t.me/TeamUltroid",
                        description="(c) TeamUltroid",
                        text=MSG,
                        thumb=InputWebDocument(
                            "https://graph.org/file/dde85d441fa051a0d7d1d.jpg",
                            0,
                            "image/jpeg",
                            [],
                        ),
                        buttons=IN_BTTS,
                    )
                ]
                return await event.answer(
                    res,
                    switch_pm=f"🤖: Assistant of {OWNER}",
                    switch_pm_param="start",
                )
            try:
                await func(event)
            except QueryIdInvalidError:
                pass
            except Exception as er:
                err = format_exc()

                def error_text():
                    return f"**#ERROR #INLINE**\n\nQuery: `{asst.me.username} {pattern}`\n\n**Traceback:**\n`{format_exc()}`"

                LOGS.exception(er)
                try:
                    await event.answer(
                        [
                            await event.builder.article(
                                title="Unhandled Exception has Occured!",
                                text=error_text(),
                                buttons=Button.url(
                                    "Report", "https://t.me/UltroidSupportChat"
                                ),
                            )
                        ]
                    )
                except QueryIdInvalidError:
                    LOGS.exception(err)
                except Exception as er:
                    LOGS.exception(er)
                    await asst.send_message(udB.get_key("LOG_CHANNEL"), error_text())

        asst.add_event_handler(wrapper, InlineQuery(pattern=pattern, **kwargs))

    return don
