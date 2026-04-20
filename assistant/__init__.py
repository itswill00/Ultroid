# Ultroid - Assistant Bot System
# (c) TeamUltroid

from telethon import Button, custom

from plugins import ATRA_COL, InlinePlugin
from pyUltroid import *
from pyUltroid import _ult_cache, udB
from pyUltroid._misc import owner_and_sudos
from pyUltroid._misc._assistant import asst_cmd, callback, in_pattern
from pyUltroid.fns.helper import *
from pyUltroid.fns.tools import get_stored_file
from strings import get_languages, get_string

# Lazy Properties for Owner Identity
# We use udB for ID to prevent early-startup AttributeError
OWNER_ID = udB.get_key("OWNER_ID") or 0
OWNER_NAME = "Owner" # Default fallback

AST_PLUGINS = {}

# The dynamic loader in pyUltroid/startup/loader.py handles loading submodules.
# Explicit imports are removed here to prevent circular dependency crashes.

async def setit(event, name, value):
    try:
        udB.set_key(name, value)
    except BaseException as er:
        LOGS.exception(er)
        return await event.edit("`Something Went Wrong`")


def get_back_button(name):
    return [Button.inline("« Bᴀᴄᴋ", data=f"{name}")]
