# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/TeamUltroid/pyUltroid/blob/main/LICENSE>.

import os
import sys
import telethonpatch
from .version import __version__
from .fns import KEEP_SAFE

run_as_module = __package__ in sys.argv or sys.argv[0] == "-m"


class ULTConfig:
    lang = "en"
    thumb = "resources/extras/ultroid.jpg"


if run_as_module:
    import time

    from .configs import Var
    from .startup import *
    from .startup._database import UltroidDB
    from .startup.BaseClient import UltroidClient
    from .startup.connections import validate_session, vc_connection
    from .startup.funcs import _version_changes, autobot, enable_inline, update_envs
    from .version import ultroid_version

    if not os.path.exists("./plugins"):
        LOGS.error(
            "'plugins' folder not found!\nMake sure that, you are on correct path."
        )
        exit()

    start_time = time.time()
    _ult_cache = {}
    _ignore_eval = []

    udB = UltroidDB()
    update_envs()

    LOGS.info(f"Connecting to {udB.name}...")
    if udB.ping():
        LOGS.info(f"Connected to {udB.name} Successfully!")

    # ── Runtime Mode Resolution ─────────────────────────────────────────
    # Priority: .env RUNTIME_MODE > DB RUNTIME_MODE > legacy DB flags
    _mode_raw = (Var.RUNTIME_MODE or udB.get_key("RUNTIME_MODE") or "").lower().strip()

    if _mode_raw in ("user", "bot", "dual"):
        RUNTIME_MODE = _mode_raw
    else:
        # Backward compat: migrate from old separate DB flag names
        if udB.get_key("BOTMODE") or udB.get_key("BOT_MODE"):
            RUNTIME_MODE = "bot"
        elif udB.get_key("USER_MODE"):
            RUNTIME_MODE = "user"
        else:
            RUNTIME_MODE = "dual"

    # Derived booleans — kept for backward compat with existing plugin code
    USER_MODE = (RUNTIME_MODE == "user")
    BOT_MODE  = (RUNTIME_MODE == "bot")
    DUAL_MODE = (RUNTIME_MODE == "dual")
    LOGS.info(f"[MODE] Runtime: {RUNTIME_MODE.upper()}")

    # ── Client Initialization ───────────────────────────────────────────
    if RUNTIME_MODE in ("user", "dual"):
        # Userbot required — validate and connect SESSION
        ultroid_bot = UltroidClient(
            validate_session(Var.SESSION or udB.get_key("SESSION"), LOGS),
            udB=udB,
            app_version=ultroid_version,
            device_model="Ultroid",
        )
        ultroid_bot.run_in_loop(autobot())
    else:
        # bot mode — no SESSION needed
        ultroid_bot = None

    if RUNTIME_MODE == "user":
        # No separate assistant bot — userbot handles everything
        if not (Var.BOT_TOKEN or udB.get_key("BOT_TOKEN")):
            LOGS.warning(
                "[MODE] RUNTIME_MODE=user: BOT_TOKEN not set — "
                "inline help menu will be unavailable."
            )
        asst = ultroid_bot  # alias — same client

    elif RUNTIME_MODE == "bot":
        # Bot-only — SESSION not used, assistant bot is primary
        _token = udB.get_key("BOT_TOKEN") or Var.BOT_TOKEN
        if not _token:
            LOGS.critical(
                '"BOT_TOKEN" is required for RUNTIME_MODE=bot. '
                "Set it in .env or database."
            )
            sys.exit()
        asst = UltroidClient("asst", bot_token=_token, udB=udB)
        ultroid_bot = asst  # alias — same client

    else:
        # Dual mode — both clients active (classic Ultroid)
        _token = udB.get_key("BOT_TOKEN") or Var.BOT_TOKEN
        if not _token:
            LOGS.warning(
                "[MODE] RUNTIME_MODE=dual: BOT_TOKEN not set — "
                "assistant bot features unavailable."
            )
        asst = UltroidClient("asst", bot_token=_token, udB=udB)

    # ── Post-initialization ─────────────────────────────────────────────
    if BOT_MODE:
        # Restore ultroid_bot.me from stored OWNER_ID (needed by helper fns)
        if udB.get_key("OWNER_ID"):
            try:
                ultroid_bot.me = ultroid_bot.run_in_loop(
                    ultroid_bot.get_entity(udB.get_key("OWNER_ID"))
                )
            except Exception as er:
                LOGS.exception(er)
    elif DUAL_MODE:
        # Enable inline if not already configured
        if not asst.me.bot_inline_placeholder and asst._bot:
            ultroid_bot.run_in_loop(enable_inline(ultroid_bot, asst.me.username))


    vcClient = vc_connection(udB, ultroid_bot)

    _version_changes(udB)

    HNDLR = udB.get_key("HNDLR") or "."
    DUAL_HNDLR = udB.get_key("DUAL_HNDLR") or "/"
    SUDO_HNDLR = udB.get_key("SUDO_HNDLR") or HNDLR
else:
    print("pyUltroid 2022 © TeamUltroid")

    from logging import getLogger

    LOGS = getLogger("pyUltroid")

    ultroid_bot = asst = udB = vcClient = None
