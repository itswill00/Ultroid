# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/TeamUltroid/pyUltroid/blob/main/LICENSE>.

import os

from decouple import config

from .. import *
from ..dB._core import HELP
from ..loader import Loader
from . import *
from .utils import load_addons


def _after_load(loader, module, plugin_name=""):
    if not module or plugin_name.startswith("_"):
        return

    # Clean plugin name: remove path and .py extension
    p_name = plugin_name.split("/")[-1].split("\\")[-1].replace(".py", "")

    # Ensure key exists in global HELP
    key = loader.key
    if key not in HELP:
        HELP[key] = {}

    # Store plugin in HELP for counting and reference
    HELP[key][p_name] = module.__doc__ or "No description available."


def load_other_plugins(addons=None, pmbot=None, manager=None, vcbot=None):
    # Load Essential Plugins synchronously (Official ones)
    _exclude = udB.get_key("EXCLUDE_OFFICIAL") or config("EXCLUDE_OFFICIAL", None)
    _exclude = _exclude.split() if _exclude else []
    _in_only = udB.get_key("INCLUDE_ONLY") or config("INCLUDE_ONLY", None)
    _in_only = _in_only.split() if _in_only else []
    
    # Official plugins are essential, load them but exclude non-core if requested
    Loader().load(include=_in_only, exclude=_exclude, after_load=_after_load)

    # Move non-essential plugins to background loading
    async def _bg_plugin_loader():
        # for assistant
        if not USER_MODE and not udB.get_key("DISABLE_AST_PLUGINS"):
            _ast_exc = ["pmbot", "games", "ytdl"]
            Loader(path="assistant").load(
                log=False, exclude=_ast_exc, after_load=_after_load
            )

        # for addons
        if addons:
            if os.path.exists("addons"):
                _exclude_a = (udB.get_key("EXCLUDE_ADDONS") or "").split()
                _in_only_a = (udB.get_key("INCLUDE_ADDONS") or "").split()
                Loader(path="addons", key="Addons").load(
                    func=load_addons,
                    include=_in_only_a,
                    exclude=_exclude_a,
                    after_load=_after_load,
                    load_all=True,
                )

        if not USER_MODE:
            if manager:
                Loader(path="assistant/manager", key="Group Manager").load()
            if pmbot:
                Loader(path="assistant/pmbot.py").load(log=False)

        # vc bot
        if vcbot and (vcClient and not vcClient.me.bot):
            try:
                import pytgcalls
                if os.path.exists("vcbot"):
                    Loader(path="vcbot", key="VCBot").load(after_load=_after_load)
            except Exception:
                pass
        
        LOGS.info("Efficiency | All Background Plugins Loaded.")

    # Execute background loader
    try:
        from .. import ultroid_bot
        ultroid_bot.loop.create_task(_bg_plugin_loader())
    except Exception as e:
        LOGS.error(f"Lazy Loader | Failed to start background task: {e}")
