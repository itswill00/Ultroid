# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.
"""
» Commands Available -

• `{i}addsudo`
    Add Sudo Users by replying to user or using <space> separated userid(s)

• `{i}delsudo`
    Remove Sudo Users by replying to user or using <space> separated userid(s)

• `{i}listsudo`
    List all sudo users.

• `{i}asstsudo <on/off>`
    Toggle Assistant Bot response for Sudo users. 
    If enabled, the Bot (Assistant) will respond to Sudoer commands instead of your User Account.
"""

from telethon.tl.types import User

from pyUltroid._misc import SUDO_M, refresh_all, sudoers
from . import OWNER_NAME, get_string, inline_mention, udB, ultroid_bot, ultroid_cmd


@ultroid_cmd(pattern="addsudo( (.*)|$)", fullsudo=True)
async def _(ult):
    inputs = ult.pattern_match.group(1).strip()
    if ult.reply_to_msg_id:
        replied_to = await ult.get_reply_message()
        id = replied_to.sender_id
        name = await replied_to.get_sender()
    elif inputs:
        try:
            id = await ult.client.parse_id(inputs)
        except ValueError:
            try:
                id = int(inputs)
            except ValueError:
                id = inputs
        try:
            name = await ult.client.get_entity(int(id))
        except BaseException:
            name = None
    elif ult.is_private:
        id = ult.chat_id
        name = await ult.get_chat()
    else:
        return await ult.eor(get_string("sudo_1"), time=5)
    if name and isinstance(name, User) and (name.bot or name.verified):
        return await ult.eor(get_string("sudo_4"))
    name = inline_mention(name) if name else f"`{id}`"
    if id == ultroid_bot.uid:
        mmm = get_string("sudo_2")
    elif id in sudoers():
        mmm = f"{name} `is already a SUDO User ...`"
    else:
        udB.set_key("SUDO", "True")
        key = sudoers()
        key.append(id)
        udB.set_key("SUDOS", key)
        refresh_all()
        mmm = f"**Added** {name} **as SUDO User**"
    await ult.eor(mmm, time=5)


@ultroid_cmd(pattern="addfullsudo( (.*)|$)", owner_only=True)
async def _(ult):
    # Only the real owner can add fullsudos
    if ult.sender_id != ultroid_bot.uid:
        return await ult.eor("`Only the Account Owner can manage Full Sudoers.`", time=5)

    inputs = ult.pattern_match.group(1).strip()
    if ult.reply_to_msg_id:
        replied_to = await ult.get_reply_message()
        id = replied_to.sender_id
        name = await replied_to.get_sender()
    elif inputs:
        try:
            id = await ult.client.parse_id(inputs)
        except ValueError:
            try:
                id = int(inputs)
            except ValueError:
                id = inputs
        try:
            name = await ult.client.get_entity(int(id))
        except BaseException:
            name = None
    else:
        return await ult.eor("`Reply to a user or provide ID to add as Full Sudo.`", time=5)

    if name and isinstance(name, User) and (name.bot or name.verified):
        return await ult.eor(get_string("sudo_4"))
    
    name = inline_mention(name) if name else f"`{id}`"
    full_sudos = SUDO_M.fullsudos
    
    if id == ultroid_bot.uid:
        mmm = "`You are the owner, you already have full access.`"
    elif id in full_sudos:
        mmm = f"{name} `is already a Full Sudo User.`"
    else:
        key = udB.get_key("FULLSUDO") or []
        if isinstance(key, str):
            key = [int(x) for x in key.split()]
        key.append(id)
        udB.set_key("FULLSUDO", key)
        refresh_all()
        mmm = f"**Elevated** {name} **to Full SUDO Access.**"
    await ult.eor(mmm, time=5)


@ultroid_cmd(pattern="delsudo( (.*)|$)", fullsudo=True)
async def _(ult):
    inputs = ult.pattern_match.group(1).strip()
    if ult.reply_to_msg_id:
        replied_to = await ult.get_reply_message()
        id = replied_to.sender_id
        name = await replied_to.get_sender()
    elif inputs:
        try:
            id = await ult.client.parse_id(inputs)
        except ValueError:
            try:
                id = int(inputs)
            except ValueError:
                id = inputs
        try:
            name = await ult.client.get_entity(int(id))
        except BaseException:
            name = None
    elif ult.is_private:
        id = ult.chat_id
        name = await ult.get_chat()
    else:
        return await ult.eor(get_string("sudo_1"), time=5)
    name = inline_mention(name) if name else f"`{id}`"
    if id not in sudoers():
        mmm = f"{name} `wasn't a SUDO User ...`"
    else:
        key = sudoers()
        key.remove(id)
        udB.set_key("SUDOS", key)
        refresh_all()
        mmm = f"**Removed** {name} **from SUDO User(s)**"
    await ult.eor(mmm, time=5)


@ultroid_cmd(pattern="delfullsudo( (.*)|$)", owner_only=True)
async def _(ult):
    if ult.sender_id != ultroid_bot.uid:
        return await ult.eor("`Only the Account Owner can manage Full Sudoers.`", time=5)

    inputs = ult.pattern_match.group(1).strip()
    if ult.reply_to_msg_id:
        replied_to = await ult.get_reply_message()
        id = replied_to.sender_id
        name = await replied_to.get_sender()
    elif inputs:
        try:
            id = await ult.client.parse_id(inputs)
        except ValueError:
            try:
                id = int(inputs)
            except ValueError:
                id = inputs
        try:
            name = await ult.client.get_entity(int(id))
        except BaseException:
            name = None
    else:
        return await ult.eor("`Reply to a user or provide ID to remove from Full Sudo.`", time=5)

    name = inline_mention(name) if name else f"`{id}`"
    full_sudos = SUDO_M.fullsudos
    if id not in full_sudos:
        mmm = f"{name} `is not a Full Sudo User.`"
    elif id == ultroid_bot.uid:
        mmm = "`You cannot remove yourself from Full Sudo.`"
    else:
        key = udB.get_key("FULLSUDO") or []
        if isinstance(key, str):
            key = [int(x) for x in key.split()]
        if id in key:
            key.remove(id)
        udB.set_key("FULLSUDO", key)
        refresh_all()
        mmm = f"**Demoted** {name} **from Full SUDO Access.**"
    await ult.eor(mmm, time=5)


@ultroid_cmd(
    pattern="listsudo$",
    fullsudo=True,
)
async def _(ult):
    sudos = sudoers()
    fullsudos = SUDO_M.fullsudos
    if not sudos and len(fullsudos) <= 1:
        return await ult.eor(get_string("sudo_3"), time=5)
    
    msg = f"• {inline_mention(ultroid_bot.me)} ( `{ultroid_bot.uid}` ) [ **OWNER** ]\n"
    
    # Process Full Sudoers first
    for i in fullsudos:
        if i == ultroid_bot.uid:
            continue
        try:
            name = await ult.client.get_entity(int(i))
        except BaseException:
            name = None
        n = inline_mention(name) if name else f"`{i}`"
        msg += f"• {n} ( `{i}` ) [ **FULL SUDO** ]\n"

    # Process Normal Sudoers
    for i in sudos:
        if i in fullsudos:
            continue
        try:
            name = await ult.client.get_entity(int(i))
        except BaseException:
            name = None
        n = inline_mention(name) if name else f"`{i}`"
        msg += f"• {n} ( `{i}` ) [ **SUDO** ]\n"

    m = udB.get_key("SUDO") or True
    return await ult.eor(
        f"**SUDO MODE : {m}\n\nList of Authorized Users :**\n{msg}", link_preview=False
    )


@ultroid_cmd(pattern="asstsudo( (on|off)|$)", fullsudo=True)
async def toggle_asst_sudo(ult):
    match = ult.pattern_match.group(2)
    if not match:
        curr = udB.get_key("ASST_SUDO_RESPOND") or False
        return await ult.eor(f"**Assistant Sudo Response is currently:** `{curr}`")
    
    if match == "on":
        udB.set_key("ASST_SUDO_RESPOND", True)
        await ult.eor("✅ **Assistant Bot will now respond to Sudo commands.**")
    else:
        udB.del_key("ASST_SUDO_RESPOND")
        await ult.eor("» **Assistant Bot response for Sudo disabled.**")
