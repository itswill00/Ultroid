# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/TeamUltroid/pyUltroid/blob/main/LICENSE>.

"""Automatic colored inline buttons.

Telegram Bot API 9.4 (February 2026) introduced ``style`` on inline
keyboard buttons, rendered by clients as colors:

    * primary  -> blue
    * success  -> green
    * danger   -> red
    * none     -> default/secondary

Telethon >= 1.44 exposes the same field through ``KeyboardButtonStyle``.
Instead of decorating every single ``Button.inline`` call in the codebase,
this module patches ``telethon.Button`` once so every inline button created
by Ultroid (official plugins, addons and custom plugins alike) gets a style
based on its label, unless the caller passed an explicit style.
"""

import re

from telethon import Button

# Small-caps / fancy unicode letters used all over Ultroid button labels
# (e.g. "« Bᴀᴄᴋ", "Cʟᴏꜱᴇ", "Dᴇʟᴇᴛᴇ") must be normalized before matching.
_NORMALIZE = str.maketrans(
    {
        "ᴀ": "a",
        "ʙ": "b",
        "ᴄ": "c",
        "ᴅ": "d",
        "ᴇ": "e",
        "ꜰ": "f",
        "ɢ": "g",
        "ʜ": "h",
        "ɪ": "i",
        "ᴊ": "j",
        "ᴋ": "k",
        "ʟ": "l",
        "ᴍ": "m",
        "ɴ": "n",
        "ᴏ": "o",
        "ᴘ": "p",
        "ǫ": "q",
        "ꞯ": "q",
        "ʀ": "r",
        "ꜱ": "s",
        "ᴛ": "t",
        "ᴜ": "u",
        "ᴠ": "v",
        "ᴡ": "w",
        "x": "x",
        "ʏ": "y",
        "ᴢ": "z",
    }
)

_DANGER_WORDS = (
    "delete",
    "del",
    "remove",
    "stop",
    "cancel",
    "kill",
    "end",
    "leave",
    "reset",
    "purge",
    "clear",
    "ban",
    "kick",
    "mute",
    "warn",
    "uninstall",
    "disable",
    "close",
)

_SUCCESS_WORDS = (
    "confirm",
    "yes",
    "ok",
    "okay",
    "done",
    "start",
    "play",
    "resume",
    "save",
    "add",
    "approve",
    "accept",
    "join",
    "subscribe",
    "enable",
    "unban",
    "unmute",
    "install",
    "continue",
    "next",
    "open",
    "proceed",
)

_PATTERNS = {
    style: tuple(re.compile(rf"(?<!\w){word}(?!\w)") for word in words)
    for style, words in (("danger", _DANGER_WORDS), ("success", _SUCCESS_WORDS))
}


def detect_style(text: str) -> str:
    """Pick a button color from its label."""
    normalized = str(text).lower().translate(_NORMALIZE)
    for style in ("danger", "success"):
        if any(pattern.search(normalized) for pattern in _PATTERNS[style]):
            return style
    return "primary"


def patch_button_styles() -> None:
    """Patch ``telethon.Button`` so inline buttons are colored by default."""
    if getattr(Button, "_ultroid_styled", False):
        return

    _inline = Button.inline
    _url = Button.url
    _switch_inline = Button.switch_inline
    _auth = Button.auth

    def inline(text, data=None, style=None, icon=None):
        return _inline(text, data, style=style or detect_style(text), icon=icon)

    def url(text, url=None, style=None, icon=None):
        return _url(text, url, style=style or detect_style(text), icon=icon)

    def switch_inline(text, query="", same_peer=False, style=None, icon=None):
        return _switch_inline(
            text,
            query,
            same_peer,
            style=style or detect_style(text),
            icon=icon,
        )

    def auth(
        text,
        url=None,
        style=None,
        icon=None,
        *,
        bot=None,
        write_access=False,
        fwd_text=None,
    ):
        return _auth(
            text,
            url,
            style=style or detect_style(text),
            icon=icon,
            bot=bot,
            write_access=write_access,
            fwd_text=fwd_text,
        )

    Button.inline = staticmethod(inline)
    Button.url = staticmethod(url)
    Button.switch_inline = staticmethod(switch_inline)
    Button.auth = staticmethod(auth)
    Button._ultroid_styled = True
