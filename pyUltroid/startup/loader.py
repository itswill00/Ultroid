# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/TeamUltroid/pyUltroid/blob/main/LICENSE>.

import os
import subprocess
import sys
from shutil import rmtree

from decouple import config
from git import Repo

from .. import *
from ..dB._core import HELP
from ..loader import Loader
from . import *
from .utils import load_addons


def _after_load(loader, module, plugin_name=""):
    # Registration optimization: only store keys for counting.
    # Help content will be fetched on-demand.
    if not module or plugin_name.startswith("_"):
        return
    if loader.key not in HELP:
        HELP[loader.key] = {}
    HELP[loader.key][plugin_name] = module.__doc__ or "No description available."


def load_other_plugins(addons=None, pmbot=None, manager=None, vcbot=None):

    # for official
    _exclude = udB.get_key("EXCLUDE_OFFICIAL") or config("EXCLUDE_OFFICIAL", None)
    _exclude = _exclude.split() if _exclude else []
    
    # Force Termux Exclusions to speed up boot
    _termux_force = "autocorrect autopic audiotools compressor forcesubscribe fedutils gdrive glitch instagram nsfwfilter nightmode pdftools profanityfilter writer youtube imagetools twitter games ytdl converter mediatools qrcode search stickertools"
    for _p in _termux_force.split():
        if _p not in _exclude:
            _exclude.append(_p)

    # "INCLUDE_ONLY" was added to reduce Big List in "EXCLUDE_OFFICIAL" Plugin
    _in_only = udB.get_key("INCLUDE_ONLY") or config("INCLUDE_ONLY", None)
    _in_only = _in_only.split() if _in_only else []
    Loader().load(include=_in_only, exclude=_exclude, after_load=_after_load)

    # for assistant
    if not USER_MODE and not udB.get_key("DISABLE_AST_PLUGINS"):
        _ast_exc = ["pmbot", "games", "ytdl"] # Skip known slow assistant plugins
        Loader(path="assistant").load(
            log=False, exclude=_ast_exc, after_load=_after_load
        )

    # for addons
    if addons:
        if not os.path.exists("addons"):
            LOGS.warning("Addons folder not found. Skipping addons loading.")
        else:
            _exclude = udB.get_key("EXCLUDE_ADDONS")
            _exclude = _exclude.split() if _exclude else []
            
            # Also exclude heavy addons in Termux
            _heavy_addons = "imagetools nightmode nsfwfilter autocorrect converter memify pdftools qrcode search stickertools"
            for _a in _heavy_addons.split():
                if _a not in _exclude:
                    _exclude.append(_a)
            _in_only = udB.get_key("INCLUDE_ADDONS")
            _in_only = _in_only.split() if _in_only else []

            Loader(path="addons", key="Addons").load(
                func=load_addons,
                include=_in_only,
                exclude=_exclude,
                after_load=_after_load,
                load_all=True,
            )

    if not USER_MODE:
        # group manager
        if manager:
            Loader(path="assistant/manager", key="Group Manager").load()

        # chat via assistant
        if pmbot:
            Loader(path="assistant/pmbot.py").load(log=False)

    # vc bot
    if vcbot and (vcClient and not vcClient.me.bot):
        try:
            import pytgcalls  # ignore: pylint

            if os.path.exists("vcbot"):
                try:
                    if not os.path.exists("vcbot/downloads"):
                        os.mkdir("vcbot/downloads")
                    Loader(path="vcbot", key="VCBot").load(after_load=_after_load)
                except FileNotFoundError as e:
                    LOGS.error(f"{e} Skipping VCBot Installation.")
            else:
                LOGS.warning("VCBot folder not found. Skipping VCBot loading.")
        except ModuleNotFoundError:
            LOGS.error("'pytgcalls' not installed!\nSkipping loading of VCBOT.")
