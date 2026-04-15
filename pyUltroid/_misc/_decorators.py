# Altroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/TeamUltroid/pyUltroid/blob/main/LICENSE>.

import asyncio
import inspect
import re
import sys
from io import BytesIO
from pathlib import Path
from time import gmtime, strftime
from traceback import format_exc

from telethon import Button
from telethon import __version__ as telever
from telethon import events
from telethon.errors.common import AlreadyInConversationError
from telethon.errors.rpcerrorlist import (
    AuthKeyDuplicatedError,
    BotInlineDisabledError,
    BotMethodInvalidError,
    ChatSendInlineForbiddenError,
    ChatSendMediaForbiddenError,
    ChatSendStickersForbiddenError,
    FloodWaitError,
    MessageDeleteForbiddenError,
    MessageIdInvalidError,
    MessageNotModifiedError,
    UserIsBotError,
)
from telethon.events import MessageEdited, NewMessage
from telethon.utils import get_display_name

from pyUltroid.exceptions import DependencyMissingError
from strings import get_string

from ._wrappers import eod, eor
from .. import *
from .. import _ignore_eval
from ..dB import DEVLIST
from ..dB._core import LIST, LOADED
from ..fns.admins import admin_check
from ..fns.helper import bash
from ..fns.helper import time_formatter as tf
from ..version import __version__ as pyver
from ..version import ultroid_version as ult_ver
from . import SUDO_M, owner_and_sudos, ULT_CONFIG

# Static Info for logging (optimized)
_SYS_INFO = f"""
**Py-Ultroid Version:** `{pyver}`
**Ultroid Version:** `{ult_ver}`
**Telethon Version:** `{telever}`
**Hosted At:** `{HOSTED_ON}`
"""

def compile_pattern(data, hndlr):
    if data.startswith("^"):
        data = data[1:]
    if data.startswith("."):
        data = data[1:]
    if hndlr in [" ", "NO_HNDLR"]:
        return re.compile("^" + data)
    return re.compile("\\" + hndlr + data)

async def command_logger(ult, pattern):
    if not ULT_CONFIG.get("COMMAND_LOGGER"):
        return
    log_channel = ULT_CONFIG.get("LOG_CHANNEL")
    if not log_channel:
        return
    try:
        if pattern:
            command_name = pattern
        else:
            text = ult.text or ""
            parts = text.split()
            command_name = parts[0].lstrip(HNDLR) if parts else "unknown"
    except (AttributeError, IndexError):
        command_name = "unknown"
    LOGS.info(f"Command '{command_name}' executed by {ult.sender_id} in {ult.chat_id}")
    try:
        await asst.send_message(
            log_channel,
            f"Command `{command_name}` executed by `{ult.sender_id}` in `{ult.chat_id}`"
        )
    except Exception:
        pass

def ultroid_cmd(
    pattern=None, manager=False, ultroid_bot=ultroid_bot, asst=asst, **kwargs
):
    owner_only = kwargs.get("owner_only", False)
    groups_only = kwargs.get("groups_only", False)
    admins_only = kwargs.get("admins_only", False)
    fullsudo = kwargs.get("fullsudo", False)
    only_devs = kwargs.get("only_devs", False)
    func = kwargs.get("func", lambda e: not (e and e.via_bot_id))

    def decor(dec):
        async def wrapp(ult):
            # Background logging to avoid blocking
            asyncio.create_task(command_logger(ult, pattern))
            
            if not ult.out:
                if fullsudo and only_devs:
                    return
                # Scoped Sudo & Authorization Check
                if owner_only or not SUDO_M.is_authorized(ult.sender_id, pattern):
                    return

                if ult.sender_id in _ignore_eval:
                    return await eod(ult, get_string("py_d1"))
                if fullsudo and ult.sender_id not in SUDO_M.fullsudos:
                    return await eod(ult, get_string("py_d2"), time=15)
            
            chat = ult.chat
            if hasattr(chat, "title"):
                if (
                    "#noub" in chat.title.lower()
                    and not (chat.admin_rights or chat.creator)
                    and not (ult.sender_id in DEVLIST)
                ):
                    return
            
            if ult.is_private and (groups_only or admins_only):
                return await eod(ult, get_string("py_d3"))
            elif admins_only and not (chat.admin_rights or chat.creator):
                return await eod(ult, get_string("py_d5"))
            
            if only_devs and not ULT_CONFIG.get("I_DEV"):
                return await eod(ult, get_string("py_d4").format(HNDLR), time=10)

            try:
                await dec(ult)
            except FloodWaitError as fwerr:
                log_chat = ULT_CONFIG.get("LOG_CHANNEL")
                if log_chat:
                    await asst.send_message(
                        log_chat,
                        f"`FloodWaitError:\n{str(fwerr)}\n\nSleeping for {tf((fwerr.seconds + 10)*1000)}`",
                    )
                await asyncio.sleep(fwerr.seconds + 10)
                return
            except (ChatSendInlineForbiddenError, ChatSendMediaForbiddenError, ChatSendStickersForbiddenError, BotMethodInvalidError, UserIsBotError, AlreadyInConversationError, BotInlineDisabledError, DependencyMissingError) as er:
                return await eod(ult, f"`{er}`" if isinstance(er, (BotInlineDisabledError, DependencyMissingError)) else f"`{str(er)}`")
            except (MessageIdInvalidError, MessageNotModifiedError, MessageDeleteForbiddenError, AuthKeyDuplicatedError) as er:
                if not isinstance(er, (MessageNotModifiedError, MessageIdInvalidError)):
                    LOGS.exception(er)
                if isinstance(er, AuthKeyDuplicatedError):
                    log_chat = ULT_CONFIG.get("LOG_CHANNEL")
                    if log_chat:
                        await asst.send_message(log_chat, "Session String expired!")
                    sys.exit()
            except events.StopPropagation:
                raise events.StopPropagation
            except Exception as e:
                LOGS.exception(e)
                log_channel = ULT_CONFIG.get("LOG_CHANNEL")
                if not log_channel:
                    return
                
                date = strftime("%Y-%m-%d %H:%M:%S", gmtime())
                naam = get_display_name(chat)
                ftext = f"**Ultroid Client Error:** @UltroidSupportChat\n{_SYS_INFO}\n"
                ftext += f"--------START CRASH LOG--------\n**Date:** `{date}`\n**Group:** `{ult.chat_id}` {naam}\n"
                ftext += f"**Sender:** `{ult.sender_id}`\n**Event:** `{ult.text}`\n"
                ftext += f"**Traceback:**\n`{format_exc()}`\n--------END CRASH LOG--------"
                
                if len(ftext) > 4096:
                    with BytesIO(ftext.encode()) as file:
                        file.name = "logs.txt"
                        error_log = await asst.send_file(log_channel, file, caption="**Crash Log**")
                else:
                    error_log = await asst.send_message(log_channel, ftext)
                    
                if ult.out:
                    await ult.edit(f"<b><a href={error_log.message_link}>[An error occurred]</a></b>", parse_mode="html")

        # Event Handler registration logic
        allow_sudo = SUDO_M.should_allow_sudo
        _add_new = allow_sudo and HNDLR != SUDO_HNDLR
        black_list_chats = ULT_CONFIG.get("BLACKLIST_CHATS")
        chats = list(black_list_chats) if black_list_chats else None
        
        # Main Handler
        cmd = compile_pattern(pattern, HNDLR) if pattern else None
        ultroid_bot.add_event_handler(
            wrapp,
            NewMessage(
                pattern=cmd,
                outgoing=True if not allow_sudo else None,
                forwards=False,
                func=func,
                chats=chats,
                blacklist_chats=bool(chats),
            ),
        )
        
        # Sudo Handler
        if _add_new and pattern:
            scmd = compile_pattern(pattern, SUDO_HNDLR)
            ultroid_bot.add_event_handler(wrapp, NewMessage(pattern=scmd, incoming=True, forwards=False, func=func, chats=chats, blacklist_chats=bool(chats)))
            
        # Edits Handler
        if ULT_CONFIG.get("TAKE_EDITS"):
            ultroid_bot.add_event_handler(wrapp, MessageEdited(pattern=cmd, forwards=False, func=lambda x: not x.via_bot_id and not (x.is_channel and x.chat.broadcast), chats=chats, blacklist_chats=bool(chats)))

        if manager and ULT_CONFIG.get("MANAGER"):
            async def manager_cmd(ult):
                if not kwargs.get("allow_all", False) and not (await admin_check(ult, require=kwargs.get("require"))):
                    return
                if not kwargs.get("allow_pm", False) and ult.is_private:
                    return
                try:
                    await dec(ult)
                except Exception as er:
                    LOGS.exception(er)
            mcmd = compile_pattern(pattern, "/") if pattern else None
            asst.add_event_handler(manager_cmd, NewMessage(pattern=mcmd, forwards=False, incoming=True, func=func, chats=chats, blacklist_chats=bool(chats)))

        # Metadata for tracking
        file = Path(inspect.stack()[1].filename)
        if "addons/" in str(file):
            LOADED.setdefault(file.stem, []).append(wrapp)
        if pattern:
            LIST.setdefault(file.stem, []).append(pattern)
        return wrapp
    return decor
