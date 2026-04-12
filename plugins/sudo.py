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
    cmds = []
    
    if ult.reply_to_msg_id:
        replied_to = await ult.get_reply_message()
        id = replied_to.sender_id
        name = await replied_to.get_sender()
        if inputs:
            cmds = inputs.split()
    elif inputs:
        parts = inputs.split()
        user_input = parts[0]
        if len(parts) > 1:
            cmds = parts[1:]
        try:
            id = await ult.client.parse_id(user_input)
        except ValueError:
            try:
                id = int(user_input)
            except ValueError:
                id = user_input
        try:
            name = await ult.client.get_entity(id)
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
        return await ult.eor(get_string("sudo_2"), time=5)

    # Database logic
    udB.set_key("SUDO", "True")
    sudos = sudoers()
    if id not in sudos:
        sudos.append(id)
        udB.set_key("SUDOS", sudos)
    
    # Scope logic
    scoped = SUDO_M.get_scoped_sudos()
    if cmds:
        current_scope = scoped.get(id, [])
        for c in cmds:
            if c not in current_scope:
                current_scope.append(c)
        scoped[id] = current_scope
        udB.set_key("SUDO_SCOPE", scoped)
        mmm = f"**Added** {name} **as Scoped SUDO User.**\n**Allowed**: `{', '.join(current_scope)}`"
    else:
        # If no commands provided, it's a "Global Sudo" (historical behavior)
        # We ensure they are removed from scope if they were there
        if id in scoped:
            scoped.pop(id)
            udB.set_key("SUDO_SCOPE", scoped)
        mmm = f"**Added** {name} **as Global SUDO User.**"
    
    refresh_all()
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
    cmds_to_rem = []

    if ult.reply_to_msg_id:
        replied_to = await ult.get_reply_message()
        id = replied_to.sender_id
        name = await replied_to.get_sender()
        if inputs:
            cmds_to_rem = inputs.split()
    elif inputs:
        parts = inputs.split()
        user_input = parts[0]
        if len(parts) > 1:
            cmds_to_rem = parts[1:]
        try:
            id = await ult.client.parse_id(user_input)
        except ValueError:
            try:
                id = int(user_input)
            except ValueError:
                id = user_input
        try:
            name = await ult.client.get_entity(id)
        except BaseException:
            name = None
    elif ult.is_private:
        id = ult.chat_id
        name = await ult.get_chat()
    else:
        return await ult.eor(get_string("sudo_1"), time=5)

    if id not in sudoers():
        return await ult.eor(f"`User` {id} `is not in SUDO list.`", time=5)

    name = inline_mention(name) if name else f"`{id}`"
    scoped = SUDO_M.get_scoped_sudos()
    
    if cmds_to_rem and id in scoped:
        current_scope = scoped[id]
        new_scope = [repr for repr in current_scope if repr not in cmds_to_rem]
        if not new_scope:
            scoped.pop(id)
        else:
            scoped[id] = new_scope
        udB.set_key("SUDO_SCOPE", scoped)
        mmm = f"**Removed commands** `{', '.join(cmds_to_rem)}` **from** {name}."
    else:
        # Full removal
        sudos = sudoers()
        if id in sudos:
            sudos.remove(id)
            udB.set_key("SUDOS", sudos)
        if id in scoped:
            scoped.pop(id)
            udB.set_key("SUDO_SCOPE", scoped)
        mmm = f"**Removed** {name} **completely from SUDO.**"
    
    refresh_all()
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
    scoped = SUDO_M.get_scoped_sudos()
    for i in sudos:
        if i in fullsudos:
            continue
        try:
            name = await ult.client.get_entity(int(i))
        except BaseException:
            name = None
        n = inline_mention(name) if name else f"`{i}`"
        scope_text = ""
        if i in scoped:
            scope_text = f" [ **SCOPED**: `{', '.join(scoped[i])}` ]"
        else:
            scope_text = " [ **SUDO** ]"
        msg += f"• {n} ( `{i}` ){scope_text}\n"


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
