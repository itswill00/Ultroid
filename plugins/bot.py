# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

from . import get_help

__doc__ = get_help("bot")

import os
import sys
import time
from platform import python_version as pyver
from random import choice

from telethon import __version__
from telethon.errors.rpcerrorlist import (
    BotMethodInvalidError,
    ChatSendMediaForbiddenError,
)

from pyUltroid.version import __version__ as UltVer

from . import HOSTED_ON, LOGS

try:
    from git import Repo
except ImportError:
    LOGS.error("bot: 'gitpython' module not found!")
    Repo = None

from telethon.utils import resolve_bot_file_id

from . import (
    ATRA_COL,
    LOGS,
    OWNER_NAME,
    ULTROID_IMAGES,
    Button,
    Carbon,
    Telegraph,
    Var,
    allcmds,
    asst,
    bash,
    call_back,
    callback,
    def_logs,
    eor,
    get_string,
    heroku_logs,
    in_pattern,
    inline_pic,
    restart,
    shutdown,
    start_time,
    time_formatter,
    udB,
    ultroid_cmd,
    ultroid_version,
    updater,
)


def ULTPIC():
    return inline_pic() or choice(ULTROID_IMAGES)


buttons = [
    [
        Button.url(get_string("bot_3"), "https://github.com/TeamUltroid/Ultroid"),
        Button.url(get_string("bot_4"), "t.me/ultroid_next"),
    ]
]

# Will move to strings
alive_txt = """
The Ultroid Userbot

  ◍ Version - {}
  ◍ Py-Ultroid - {}
  ◍ Telethon - {}
"""

in_alive = "{}\n\n• **Version** : <code>{}</code>\n• **Core** : <code>{}</code>\n• **Python** : <code>{}</code>\n• **Uptime** : <code>{}</code>\n• **Branch** : [ {} ]"

@callback("alive")
async def alive(event):
    import psutil
    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory().percent
    text = f"📊 Server Stats 📊\n\n💻 CPU: {cpu}%\n🧠 RAM: {mem}%\n\nUltroid v{ultroid_version}"
    await event.answer(text, alert=True)


@ultroid_cmd(pattern="alive( (.*)|$)")
async def lol(ult):
    """Ultra-Premium Alive Command"""
    xx = await ult.eor("`Checking system status...`建立")
    uptime = time_formatter((time.time() - start_time) * 1000)
    pic = udB.get_key("ALIVE_PIC") or ULTPIC()
    if isinstance(pic, list):
        pic = choice(pic)
    
    # System Data
    branch = Repo().active_branch
    rev_url = Repo().remotes[0].config_reader.get("url").replace(".git", f"/tree/{branch}")
    header = udB.get_key("ALIVE_TEXT") or "<b>Ultroid Userbot</b>"
    
    # Premium HTML Template
    als = f"{header}\n\n"
    als += f"👤 <b>Owner:</b> <a href='tg://user?id={ult.sender_id}'>{OWNER_NAME}</a>\n"
    als += f"⚙️ <b>Engine:</b> <code>v{ultroid_version}</code>\n"
    als += f"🛠 <b>Core:</b> <code>{UltVer}</code>\n"
    als += f"🐍 <b>Python:</b> <code>{pyver()}</code>\n"
    als += f"⏳ <b>Uptime:</b> <code>{uptime}</code>\n"
    als += f"🎋 <b>Branch:</b> <a href='{rev_url}'>[{branch}]</a>\n\n"
    als += f"<i>System is running smoothly on {HOSTED_ON}.</i>"

    buttons = [
        [
            Button.inline("Ping", data="pkng"),
            Button.inline("Stats", data="alive"),
        ],
        [
            Button.inline("Help Menu", data="open"),
            Button.url("Support", url="https://t.me/ultroid_next")
        ],
        [Button.inline("✕ Close", data="close")]
    ]

    try:
        await asst.send_file(
            ult.chat_id,
            pic,
            caption=als,
            parse_mode="html",
            buttons=buttons,
            reply_to=ult.reply_to_msg_id
        )
        await xx.delete()
    except Exception as e:
        LOGS.exception(e)
        await xx.edit(f"<b>Error:</b> <code>{e}</code>", parse_mode="html")



@ultroid_cmd(pattern="ping$", chats=[], type=["official", "assistant"])
async def _(event):
    start = time.time()
    x = await event.eor("`Cek ping...`")
    end = round((time.time() - start) * 1000)
    uptime = time_formatter((time.time() - start_time) * 1000)
    res = f"**Latency:** `{end}ms` · **Uptime:** `{uptime}`"
    await x.edit(res)


@ultroid_cmd(
    pattern="cmds$",
)
async def cmds(event):
    await allcmds(event, Telegraph)


heroku_api = Var.HEROKU_API


@ultroid_cmd(
    pattern="restart$",
    fullsudo=True,
)
async def restartbt(ult):
    ok = await ult.eor("`Rebooting process... Please wait.`")
    call_back()

    # Standardize on JSON for reliability
    import json
    data = {"chat_id": ult.chat_id, "msg_id": ok.id}
    udB.set_key("_RESTART", json.dumps(data))

    if heroku_api:
        return await restart(ok)

    # Simple process replacement for speed and stability
    args = [sys.executable, "-m", "pyUltroid"]
    if len(sys.argv) > 1:
        args = [sys.executable, "main.py"]

    os.execl(sys.executable, *args)


@ultroid_cmd(
    pattern="shutdown$",
    fullsudo=True,
)
async def shutdownbot(ult):
    await shutdown(ult)


@ultroid_cmd(
    pattern="logs( (.*)|$)",
    chats=[],
)
async def _(event):
    opt = event.pattern_match.group(1).strip()
    file = f"ultroid{sys.argv[-1]}.log" if len(sys.argv) > 1 else "ultroid.log"
    if opt == "heroku":
        await heroku_logs(event)
    elif opt == "carbon" and Carbon:
        event = await event.eor(get_string("com_1"))
        with open(file, "r") as f:
            code = f.read()[-2500:]
        file = await Carbon(
            file_name="ultroid-logs",
            code=code,
            backgroundColor=choice(ATRA_COL),
        )
        if isinstance(file, dict):
            await event.eor(f"`{file}`")
            return
        await event.reply("**Ultroid Logs.**", file=file)
    elif opt == "open":
        with open("ultroid.log", "r") as f:
            file = f.read()[-4000:]
        return await event.eor(f"`{file}`")
    elif (
        opt.isdigit() and 5 <= int(opt) <= 100
    ):  # Check if input is a number between 10 and 100
        num_lines = int(opt)
        with open("ultroid.log", "r") as f:
            lines = f.readlines()[-num_lines:]
            file = "".join(lines)
        return await event.eor(f"`{file}`")
    else:
        await def_logs(event, file)
    await event.try_delete()


@in_pattern("alive", owner=True)
async def inline_alive(ult):
    pic = udB.get_key("ALIVE_PIC")
    if isinstance(pic, list):
        pic = choice(pic)
    uptime = time_formatter((time.time() - start_time) * 1000)
    header = udB.get_key("ALIVE_TEXT") or get_string("bot_1")
    y = Repo().active_branch
    xx = Repo().remotes[0].config_reader.get("url")
    rep = xx.replace(".git", f"/tree/{y}")
    kk = f"<a href={rep}>{y}</a>"
    als = in_alive.format(
        header, f"{ultroid_version} [{HOSTED_ON}]", UltVer, pyver(), uptime, kk
    )

    if _e := udB.get_key("ALIVE_EMOJI"):
        als = als.replace("🌀", _e)
    builder = ult.builder
    if pic:
        try:
            ext = str(pic).split(".")[-1].lower()
            if ext in ["jpg", "jpeg", "png"]:
                results = [
                    await builder.photo(
                        pic, text=als, parse_mode="html", buttons=buttons
                    )
                ]
            elif ext in ["gif", "mp4"]:
                results = [
                    await builder.gif(
                        pic, text=als, parse_mode="html", buttons=buttons
                    )
                ]
            else:
                if _pic := resolve_bot_file_id(pic):
                    pic = _pic
                    buttons.insert(
                        0, [Button.inline(get_string("bot_2"), data="alive")]
                    )
                results = [
                    await builder.document(
                        pic,
                        title="Inline Alive",
                        description="@TeamUltroid",
                        text=als,
                        parse_mode="html",
                        buttons=buttons,
                    )
                ]
            return await ult.answer(results)
        except BaseException as er:
            LOGS.exception(er)
    result = [
        await builder.article(
            "Alive", text=als, parse_mode="html", link_preview=False, buttons=buttons
        )
    ]
    await ult.answer(result)


@ultroid_cmd(pattern="update( (.*)|$)")
async def _(e):
    """Update Ultroid with a minimalist UI"""
    opt = e.pattern_match.group(1).strip()
    if "now" in opt or "fast" in opt:
        xx = await e.eor("`Force update started...`")
        await bash("git pull -f && pip3 install -r requirements.txt --break-system-packages")
        await xx.edit("`Successfully updated! Restarting...`")
        return os.execl(sys.executable, "python3", "-m", "pyUltroid")

    xx = await e.eor("`Checking for updates...`")
    update_avail, changelog, _ = await updater()
    
    if not update_avail:
        return await xx.edit(f"✅ **Your Ultroid is already up-to-date.**", link_preview=False)

    # Minimalist Changelog UI via Assistant
    msg = f"{changelog}\n\n**Do you want to update now?**"
    buttons = [
        [Button.inline("✅ Update Now", data="do_update"), 
         Button.inline("❌ Cancel", data="cancel_update")]
    ]
    
    await asst.send_message(e.chat_id, msg, parse_mode="html", buttons=buttons, link_preview=False)
    await xx.delete()

@callback("do_update", owner=True)
async def exec_update(event):
    await event.edit("`Starting update... Please wait.`")
    await bash("git pull -f && pip3 install -r requirements.txt --break-system-packages")
    await event.edit("`Update successful! Bot is restarting...`")
    os.execl(sys.executable, "python3", "-m", "pyUltroid")

@callback("cancel_update", owner=True)
async def cancel_upd(event):
    await event.edit("❌ **Update canceled.**")


@callback("updtavail", owner=True)
async def updava(event):
    await event.delete()
    await asst.send_file(
        udB.get_key("LOG_CHANNEL"),
        ULTPIC(),
        caption="• **Update Available** •",
        force_document=False,
        buttons=Button.inline("Changelogs", data="changes"),
    )
