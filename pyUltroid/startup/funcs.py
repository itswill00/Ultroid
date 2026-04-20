# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/TeamUltroid/pyUltroid/blob/main/LICENSE>.

import asyncio
import os
import random
import re
import shutil
import time
from datetime import datetime, timezone as dt_timezone
from random import randint

from ..configs import Var

try:
    from pytz import timezone
except ImportError:
    timezone = None

from telethon.errors import (
    ChannelsTooMuchError,
    ChatAdminRequiredError,
    MessageIdInvalidError,
    MessageNotModifiedError,
    UserNotParticipantError,
)
from telethon.tl.custom import Button
from telethon.tl.functions.channels import (
    CreateChannelRequest,
    EditAdminRequest,
    EditPhotoRequest,
    InviteToChannelRequest,
)
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.contacts import UnblockRequest
from telethon.tl.types import (
    ChatAdminRights,
    ChatPhotoEmpty,
    InputChatUploadedPhoto,
    InputMessagesFilterDocument,
)
from telethon.utils import get_peer_id
from decouple import config, RepositoryEnv
from .. import LOGS, ULTConfig
from ..fns import KEEP_SAFE
from ..fns.helper import download_file, inline_mention, updater

db_url = 0
REDIS_KEEPALIVE_KEY = "KEEP_ACTIVE"
REDIS_KEEPALIVE_INTERVAL_SECONDS = 7 * 24 * 60 * 60


async def autoupdate_local_database():
    from .. import Var, asst, udB, ultroid_bot

    global db_url
    db_url = (
        udB.get_key("TGDB_URL") or Var.TGDB_URL or ultroid_bot._cache.get("TGDB_URL")
    )
    if db_url:
        _split = db_url.split("/")
        _channel = _split[-2]
        _id = _split[-1]
        try:
            await asst.edit_message(
                int(_channel) if _channel.isdigit() else _channel,
                message=_id,
                file="database.json",
                text="**Do not delete this file.**",
            )
        except MessageNotModifiedError:
            return
        except MessageIdInvalidError:
            pass
    try:
        LOG_CHANNEL = (
            udB.get_key("LOG_CHANNEL")
            or Var.LOG_CHANNEL
            or asst._cache.get("LOG_CHANNEL")
            or "me"
        )
        msg = await asst.send_message(
            LOG_CHANNEL, "**Do not delete this file.**", file="database.json"
        )
        asst._cache["TGDB_URL"] = msg.message_link
        udB.set_key("TGDB_URL", msg.message_link)
    except Exception as ex:
        LOGS.error(f"Error on autoupdate_local_database: {ex}")


def update_envs():
    """Update Var. attributes to udB"""
    from .. import udB
    _envs = [*list(os.environ)]
    if ".env" in os.listdir("."):
        try:
            [_envs.append(_) for _ in list(RepositoryEnv(config._find_file(".")).data)]
        except Exception:
            pass
    for envs in _envs:
        if (
            envs
            in [
                "LOG_CHANNEL",
                "BOT_TOKEN",
                "BOTMODE",
                "DUAL_MODE",
                "language",
                "SESSION",
                "API_ID",
                "API_HASH",
            ]
            or envs in udB.keys()
        ):
            _value = os.environ.get(envs)
            if not _value:
                try:
                    _value = config(envs, default=None)
                except Exception:
                    _value = None
            if _value:
                udB.set_key(envs, _value)


async def startup_stuff():
    from .. import udB

    _paths = ["resources/auth", "resources/downloads"]
    for path in _paths:
        if not os.path.isdir(path):
            os.mkdir(path)

    CT = udB.get_key("CUSTOM_THUMBNAIL")
    if CT:
        path = "resources/extras/thumbnail.jpg"
        ULTConfig.thumb = path
        try:
            await download_file(CT, path)
        except Exception as er:
            LOGS.exception(er)
    elif CT is False:
        ULTConfig.thumb = None
    GT = udB.get_key("GDRIVE_AUTH_TOKEN")
    if GT:
        def _write_gdrive():
            with open("resources/auth/gdrive_creds.json", "w") as t_file:
                t_file.write(GT)
        await asyncio.to_thread(_write_gdrive)

    if udB.get_key("AUTH_TOKEN"):
        udB.del_key("AUTH_TOKEN")

    MM = udB.get_key("MEGA_MAIL")
    MP = udB.get_key("MEGA_PASS")
    if MM and MP:
        def _write_mega():
            with open(".megarc", "w") as mega:
                mega.write(f"[Login]\nUsername = {MM}\nPassword = {MP}")
        await asyncio.to_thread(_write_mega)

    TZ = udB.get_key("TIMEZONE")
    if TZ and timezone:
        try:
            timezone(TZ)
            os.environ["TZ"] = TZ
            time.tzset()
        except AttributeError as er:
            LOGS.debug(er)
        except BaseException:
            LOGS.critical(
                "Incorrect Timezone ,\nCheck Available Timezone From Here https://graph.org/Ultroid-06-18-2\nSo Time is Default UTC"
            )
            os.environ["TZ"] = "UTC"
            time.tzset()


async def keep_redis_alive():
    from .. import udB

    if udB.name != "Redis":
        return

    interval = udB.get_key("REDIS_KEEPALIVE_INTERVAL")
    try:
        interval = int(interval) if interval else REDIS_KEEPALIVE_INTERVAL_SECONDS
    except (TypeError, ValueError):
        interval = REDIS_KEEPALIVE_INTERVAL_SECONDS
    interval = max(interval, 60)

    while True:
        try:
            now = datetime.now(dt_timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            udB.set_key(REDIS_KEEPALIVE_KEY, f"Updated value at {now}")
            LOGS.debug(
                "Redis keepalive updated key '%s' (next run in %s seconds).",
                REDIS_KEEPALIVE_KEY,
                interval,
            )
        except Exception as exc:
            LOGS.warning("Redis keepalive update failed: %s", exc)
        await asyncio.sleep(interval)


async def autobot():
    from .. import udB, ultroid_bot

    if udB.get_key("BOT_TOKEN"):
        return
    await ultroid_bot.start()
    LOGS.info("MAKING A TELEGRAM BOT FOR YOU AT @BotFather, Kindly Wait")
    who = ultroid_bot.me
    name = who.first_name + "'s Bot"
    if who.username:
        username = who.username + "_bot"
    else:
        username = "ultroid_" + (str(who.id))[5:] + "_bot"
    bf = "@BotFather"
    await ultroid_bot(UnblockRequest(bf))
    await ultroid_bot.send_message(bf, "/cancel")
    await asyncio.sleep(1)
    await ultroid_bot.send_message(bf, "/newbot")
    await asyncio.sleep(1)
    isdone = (await ultroid_bot.get_messages(bf, limit=1))[0].text
    if isdone.startswith("That I cannot do.") or "20 bots" in isdone:
        LOGS.critical(
            "Please make a Bot from @BotFather and add it's token in BOT_TOKEN, as an env var and restart me."
        )
        import sys

        sys.exit(1)
    await ultroid_bot.send_message(bf, name)
    await asyncio.sleep(1)
    isdone = (await ultroid_bot.get_messages(bf, limit=1))[0].text
    if not isdone.startswith("Good."):
        await ultroid_bot.send_message(bf, "My Assistant Bot")
        await asyncio.sleep(1)
        isdone = (await ultroid_bot.get_messages(bf, limit=1))[0].text
        if not isdone.startswith("Good."):
            LOGS.critical(
                "Please make a Bot from @BotFather and add it's token in BOT_TOKEN, as an env var and restart me."
            )
            import sys

            sys.exit(1)
    await ultroid_bot.send_message(bf, username)
    await asyncio.sleep(1)
    isdone = (await ultroid_bot.get_messages(bf, limit=1))[0].text
    await ultroid_bot.send_read_acknowledge("botfather")
    if isdone.startswith("Sorry,"):
        ran = randint(1, 100)
        username = "ultroid_" + (str(who.id))[6:] + str(ran) + "_bot"
        await ultroid_bot.send_message(bf, username)
        await asyncio.sleep(1)
        isdone = (await ultroid_bot.get_messages(bf, limit=1))[0].text
    if isdone.startswith("Done!"):
        token = isdone.split("`")[1]
        udB.set_key("BOT_TOKEN", token)
        await enable_inline(ultroid_bot, username)
        LOGS.info(
            f"Done. Successfully created @{username} to be used as your assistant bot!"
        )
    else:
        LOGS.info(
            "Please Delete Some Of your Telegram bots at @Botfather or Set Var BOT_TOKEN with token of a bot"
        )

        import sys

        sys.exit(1)


async def autopilot():
    from .. import asst, udB, ultroid_bot

    channel = udB.get_key("LOG_CHANNEL")
    new_channel = None
    if channel:
        try:
            chat = await ultroid_bot.get_entity(int(channel))
        except Exception as err:
            LOGS.warning(f"Failed to fetch Log Channel identity: {err}")
            udB.del_key("LOG_CHANNEL")
            channel = None
    if not channel:

        async def _save(exc):
            udB._cache["LOG_CHANNEL"] = ultroid_bot.me.id
            await asst.send_message(
                ultroid_bot.me.id, f"Failed to Create Log Channel due to {exc}.."
            )

        if ultroid_bot._bot:
            msg_ = "'LOG_CHANNEL' not found! Add it in order to use 'BOTMODE'"
            LOGS.error(msg_)
            return await _save(msg_)
        LOGS.info("Creating a Log Channel for You!")
        try:
            r = await ultroid_bot(
                CreateChannelRequest(
                    title="My Ultroid Logs",
                    about="My Ultroid Log Group\n\n Join @TeamUltroid",
                    megagroup=True,
                ),
            )
        except ChannelsTooMuchError as er:
            LOGS.critical(
                "You are in too many channels/groups. Please leave some and restart."
            )
            return await _save(str(er))
        except Exception as er:
            LOGS.error(f"Automatic Log Channel creation failed: {er}")
            return await _save(str(er))
        new_channel = True
        chat = r.chats[0]
        channel = get_peer_id(chat)
        udB.set_key("LOG_CHANNEL", channel)
    assistant = True
    try:
        await ultroid_bot.get_permissions(int(channel), asst.me.username)
    except UserNotParticipantError:
        try:
            await ultroid_bot(InviteToChannelRequest(int(channel), [asst.me.username]))
        except Exception as er:
            LOGS.warning(f"Failed to add Assistant to Log Channel: {er}")
            assistant = False
    except Exception as er:
        assistant = False
        LOGS.debug(f"Permission check for Log Channel failed: {er}")
    if assistant and new_channel:
        try:
            achat = await asst.get_entity(int(channel))
        except BaseException as er:
            achat = None
            LOGS.info("Error while getting Log channel from Assistant")
            LOGS.exception(er)
        if achat and not achat.admin_rights:
            rights = ChatAdminRights(
                add_admins=True,
                invite_users=True,
                change_info=True,
                ban_users=True,
                delete_messages=True,
                pin_messages=True,
                anonymous=False,
                manage_call=True,
            )
            try:
                await ultroid_bot(
                    EditAdminRequest(
                        int(channel), asst.me.username, rights, "Assistant"
                    )
                )
            except ChatAdminRequiredError:
                LOGS.warning("Missing admin rights to promote Assistant in Log Channel.")
            except Exception as er:
                LOGS.error(f"Assistant promotion failed: {er}")
    if isinstance(chat.photo, ChatPhotoEmpty):
        photo, _ = await download_file(
            "https://graph.org/file/27c6812becf6f376cbb10.jpg", "channelphoto.jpg"
        )
        ll = await ultroid_bot.upload_file(photo)
        try:
            await ultroid_bot(
                EditPhotoRequest(int(channel), InputChatUploadedPhoto(ll))
            )
        except BaseException as er:
            LOGS.exception(er)
        os.remove(photo)


# customize assistant


async def customize():
    from .. import asst, udB, ultroid_bot

    rem = None
    try:
        chat_id = udB.get_key("LOG_CHANNEL")
        if asst.me.photo:
            return
        LOGS.info("Customising Your Assistant Bot in @BOTFATHER")
        UL = f"@{asst.me.username}"
        if not ultroid_bot.me.username:
            sir = ultroid_bot.me.first_name
        else:
            sir = f"@{ultroid_bot.me.username}"
        file = random.choice(
            [
                "https://graph.org/file/92cd6dbd34b0d1d73a0da.jpg",
                "https://graph.org/file/a97973ee0425b523cdc28.jpg",
                "resources/extras/ultroid_assistant.jpg",
            ]
        )
        if not os.path.exists(file):
            file, _ = await download_file(file, "profile.jpg")
            rem = True
        msg = await asst.send_message(
            chat_id, "**Auto Customisation** Started on @Botfather"
        )
        await asyncio.sleep(1)
        await ultroid_bot.send_message("botfather", "/cancel")
        await asyncio.sleep(1)
        await ultroid_bot.send_message("botfather", "/setuserpic")
        await asyncio.sleep(1)
        isdone = (await ultroid_bot.get_messages("botfather", limit=1))[0].text
        if isdone.startswith("Invalid bot"):
            LOGS.info("Error while trying to customise assistant, skipping...")
            return
        await ultroid_bot.send_message("botfather", UL)
        await asyncio.sleep(1)
        await ultroid_bot.send_file("botfather", file)
        await asyncio.sleep(2)
        await ultroid_bot.send_message("botfather", "/setabouttext")
        await asyncio.sleep(1)
        await ultroid_bot.send_message("botfather", UL)
        await asyncio.sleep(1)
        await ultroid_bot.send_message(
            "botfather", f"✨ Hello ✨!! I'm Assistant Bot of {sir}"
        )
        await asyncio.sleep(2)
        await ultroid_bot.send_message("botfather", "/setdescription")
        await asyncio.sleep(1)
        await ultroid_bot.send_message("botfather", UL)
        await asyncio.sleep(1)
        await ultroid_bot.send_message(
            "botfather",
            f"✨ Powerful Ultroid Assistant Bot ✨\n✨ Master ~ {sir} ✨\n\n✨ Powered By ~ @TeamUltroid ✨",
        )
        await asyncio.sleep(2)
        await msg.edit("Completed **Auto Customisation** at @BotFather.")
        if rem:
            os.remove(file)
        LOGS.info("Customisation Done")
    except Exception as e:
        LOGS.warning(f"Assistant Bot customization failed: {e}")


async def plug(plugin_channels):
    from .. import ultroid_bot
    from .utils import load_addons

    if ultroid_bot._bot:
        LOGS.info("Plugin Channels can't be used in 'BOTMODE'")
        return
    if os.path.exists("addons") and not os.path.exists("addons/.git"):
        shutil.rmtree("addons")
    if not os.path.exists("addons"):
        os.mkdir("addons")
    if not os.path.exists("addons/__init__.py"):
        def _init_addons():
            with open("addons/__init__.py", "w") as f:
                f.write("from plugins import *\n\nbot = ultroid_bot")
        await asyncio.to_thread(_init_addons)
    LOGS.info("• Loading Plugins from Plugin Channel(s) •")
    for chat in plugin_channels:
        LOGS.info(f"{'•'*4} {chat}")
        try:
            async for x in ultroid_bot.iter_messages(
                chat, search=".py", filter=InputMessagesFilterDocument, wait_time=10
            ):
                plugin = "addons/" + x.file.name.replace("_", "-").replace("|", "-")
                if not os.path.exists(plugin):
                    await asyncio.sleep(0.6)
                    if x.text == "#IGNORE":
                        continue
                    plugin = await x.download_media(plugin)
                    # Safety check: scan for malicious patterns
                    try:
                        with open(plugin, "r") as f:
                            content = f.read()
                        for pattern in KEEP_SAFE().All:
                            if re.search(pattern, content):
                                LOGS.warning(
                                    f"PLUGIN_CHANNEL - BLOCKED - {plugin}: matched safety pattern '{pattern}'"
                                )
                                os.remove(plugin)
                                plugin = None
                                break
                    except Exception as scan_err:
                        LOGS.warning(f"Failed to scan plugin {plugin}: {scan_err}")
                        os.remove(plugin)
                        plugin = None
                    if not plugin:
                        continue
                    try:
                        load_addons(plugin)
                    except Exception as e:
                        LOGS.info(f"Ultroid - PLUGIN_CHANNEL - ERROR - {plugin}")
                        LOGS.exception(e)
                        os.remove(plugin)
        except Exception as er:
            LOGS.exception(er)




async def ready():
    from .. import asst, udB, ultroid_bot
    import platform
    import json as _json
    import time as _time
    from ..version import __version__ as pyver, ultroid_version as ult_ver
    from ..dB._core import HELP, LIST
    from telethon import __version__ as telever

    chat_id = udB.get_key("LOG_CHANNEL")
    if not chat_id:
        LOGS.warning("LOG_CHANNEL not set — skipping startup notification.")
        return

    # ── Restart Detection & Unified Data ──────────────────────
    restart_data = udB.get_key("_RESTART")
    rs_info = None
    if restart_data:
        try:
            rs_info = restart_data if isinstance(restart_data, dict) else _json.loads(restart_data)
        except Exception:
            pass

    # ── Runtime data ──────────────────────────────────────────
    boot_ts        = datetime.now(dt_timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    py_short       = platform.python_version()
    arch           = platform.machine() or "unknown"
    _raw_hosted    = getattr(ultroid_bot, "_hosted_on", None) or os.environ.get("HOSTED_ON", "local")
    hosted         = str(_raw_hosted).split("#")[0].strip() or "local"

    plugin_count   = sum(len(v) for v in LIST.values())
    official_count = len(HELP.get("Official", []))
    addon_count    = len(HELP.get("Addons", []))

    me          = ultroid_bot.me
    asst_me     = asst.me
    username    = f"@{me.username}" if me.username else me.first_name
    asst_handle = f"@{asst_me.username}" if asst_me.username else "—"

    # ── Build Human-Friendly Card ─────────────────────────────
    header_emoji = "🚀" if not rs_info else "🔄"
    status_text = "System Online" if not rs_info else "Restart Complete"
    
    CARD = (
        f"{header_emoji} **{status_text}**\n"
        f"---"
        f"\n👤 **Owner:** {username}"
        f"\n🤖 **Assistant:** {asst_handle}"
        f"\n\n🖥️ **System:** {hosted} (`{arch}`)"
        f"\n⚙️ **Engine:** `{py_short}` / `v{ult_ver}`"
        f"\n🗄️ **Database:** {udB.name}"
        f"\n🧩 **Plugins:** {plugin_count} total"
        f"\n\n⏱️ `{boot_ts}`"
    )

    if rs_info:
        # Calculate downtime
        downtime = round(_time.time() - float(rs_info.get("ts", _time.time())), 1)
        dt_str = f"{downtime / 3600:.1f}h" if downtime > 3600 else f"{downtime / 60:.1f}m" if downtime > 60 else f"{downtime}s"
        CARD += f"\n📉 **Downtime:** {dt_str}"
        
        # Version change detection
        prev_v = rs_info.get("version", "?")
        if prev_v != "?" and prev_v != str(ult_ver):
            CARD += f"\n🆙 **Update:** `{prev_v}` → `{ult_ver}`"

    # Add mode line
    _mode_label = (
        "User Only" if getattr(asst, "_bot", False) is False
        else "Bot Only" if (asst is ultroid_bot and getattr(asst, "_bot", False))
        else "Dual Mode"
    )
    CARD += f"\n🛠️ **Mode:** {_mode_label}"


    # ── Buttons ───────────────────────────────────────────────
    has_update = False
    try:
        has_update = await updater()
    except Exception:
        pass

    if getattr(asst, "_bot", False):
        BTTS = [[
            Button.inline("Ping",  data="pkng"),
            Button.inline("Help",  data="open"),
            Button.inline("Stats", data="alive"),
        ]]
        if has_update:
            BTTS.insert(0, [Button.inline("Update available", data="doupdate")])
    else:
        BTTS = None

    # ── Send Card ─────────────────────────────────────────────
    # Delete previous cards to keep logs clean
    prev_ids = [udB.get_key("LAST_UPDATE_LOG_SPAM"), udB.get_key("LAST_UPDATE_USERBOT_MSG")]
    for p_id in prev_ids:
        if p_id:
            try:
                await asst.delete_messages(chat_id, int(p_id))
            except Exception:
                pass

    card_sent = None
    try:
        card_sent = await asst.send_message(chat_id, CARD, buttons=BTTS, link_preview=False)
        LOGS.info("Startup card sent.")
    except Exception as e:
        LOGS.warning(f"Assistant failed to send startup card: {e}")
        try:
            card_sent = await ultroid_bot.send_message(chat_id, CARD, link_preview=False)
        except Exception as e2:
            LOGS.error(f"Both clients failed to send startup card: {e2}")

    if card_sent:
        udB.set_key("LAST_UPDATE_LOG_SPAM", card_sent.id)

    # Clean initial deploy mark
    if not udB.get_key("INIT_DEPLOY"):
        udB.set_key("INIT_DEPLOY", "Done")

    if not udB.get_key("NO_JOIN_CHANNEL"):
        try:
            await ultroid_bot(JoinChannelRequest("TheUltroid"))
        except Exception:
            pass


async def WasItRestart(udb):
    key = udb.get_key("_RESTART")
    if not key or not str(key).strip():
        if key:
            udb.del_key("_RESTART")
        return
    from .. import asst, ultroid_bot
    import json as _json

    try:
        data = key if isinstance(key, dict) else _json.loads(key)
        chat_id = int(data["chat_id"])
        msg_id  = int(data["msg_id"])
        
        # Professional cleanup: delete the old 'Initiating Restart' message
        # This prevents redundant notifications and keeps the chat clean.
        try:
            await asst.delete_messages(chat_id, msg_id)
        except Exception:
            try:
                await ultroid_bot.delete_messages(chat_id, msg_id)
            except Exception:
                pass
    except Exception as e:
        LOGS.debug(f"Error during WasItRestart cleanup: {e}")

    udb.del_key("_RESTART")



def _version_changes(udb):
    for _ in [
        "BOT_USERS",
        "BOT_BLS",
        "VC_SUDOS",
        "SUDOS",
        "CLEANCHAT",
        "LOGUSERS",
        "PLUGIN_CHANNEL",
        "CH_SOURCE",
        "CH_DESTINATION",
        "BROADCAST",
    ]:
        key = udb.get_key(_)
        if key and str(key)[0] != "[":
            key = udb.get(_)
            new_ = [
                int(z) if z.isdigit() or (z.startswith("-") and z[1:].isdigit()) else z
                for z in key.split()
            ]
            udb.set_key(_, new_)


async def enable_inline(ultroid_bot, username):
    bf = "BotFather"
    await ultroid_bot.send_message(bf, "/setinline")
    await asyncio.sleep(1)
    await ultroid_bot.send_message(bf, f"@{username}")
    await asyncio.sleep(1)
    await ultroid_bot.send_message(bf, "Search")
    await ultroid_bot.send_read_acknowledge(bf)
