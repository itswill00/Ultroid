# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

from . import *

START = """
✨ **Ultroid Assistant Help Menu** ✨

I am your powerful assistant bot, working alongside your UserBot to provide seamless management and utility features.

**Main Features:**
• **AdminTools:** Manage your groups effortlessly.
• **Locks:** Secure your chats with granular locks.
• **Utilities:** Handy tools for daily tasks.
• **Misc:** Fun and extra features.

Select a category below to explore more.
"""

def get_buttons():
    # Modernized button labels
    BTTS = [
        [
            Button.inline("🛡️ Admin Tools", "hlp_Admintools"),
            Button.inline("🔒 Locks", "hlp_locks"),
        ],
        [
            Button.inline("🛠️ Utilities", "hlp_Utils"),
            Button.inline("🎁 Misc", "hlp_Misc"),
        ]
    ]
    
    # Add Dual Mode Info if active
    if udB.get_key("DUAL_MODE"):
        BTTS.append([Button.inline("🚀 UserBot Commands (Dual Mode)", "hlp_dualinfo")])
    
    # Bottom buttons
    url = f"https://t.me/{asst.me.username}?startgroup=true"
    BTTS.append([Button.url("➕ Add to Group", url)])
    BTTS.append([Button.url("📢 Channel", "https://t.me/TeamUltroid"), Button.url("💬 Support", "https://t.me/UltroidSupportChat")])
    return BTTS

DUAL_INFO = """
🚀 **Dual Mode Information** 🚀

In Dual Mode, your Assistant Bot can handle many of the same commands as your UserBot using the `/` prefix.

**How it works:**
• Use `.` for UserBot commands.
• Use `/` for Assistant Bot commands.

Most plugins are synchronized between both clients for maximum reliability and efficiency.
"""

STRINGS = {
    "Admintools": ADMINTOOLS, 
    "locks": LOCKS, 
    "Utils": UTILITIES, 
    "Misc": MISC,
    "dualinfo": DUAL_INFO
}

@asst_cmd(pattern="help")
async def helpish(event):
    if not event.is_private:
        url = f"https://t.me/{asst.me.username}?start=help"
        return await event.reply(
            "**Need help?**\nContact me in Private for the full interactive menu!", 
            buttons=Button.url("📂 Open Help Menu", url)
        )
    await event.reply(START, buttons=get_buttons())

@callback("mnghome")
async def home_aja(e):
    await e.edit(START, buttons=get_buttons())

@callback(re.compile("hlp_(.*)"))
async def do_something(event):
    match = event.pattern_match.group(1).strip().decode("utf-8")
    if match in STRINGS:
        await event.edit(STRINGS[match], buttons=Button.inline("⬅️ Back", "mnghome"))
    else:
        await event.answer("Category not found!", alert=True)

