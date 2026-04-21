# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/TeamUltroid/pyUltroid/blob/main/LICENSE>.

from . import *


def main():
    import os
    import sys
    import time

    from .fns.helper import bash, time_formatter, updater
    from .startup.funcs import (
        WasItRestart,
        autopilot,
        customize,
        keep_redis_alive,
        plug,
        ready,
        startup_stuff,
    )
    from .startup.loader import load_other_plugins

    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
    except ImportError:
        pass

    # Option to Auto Update On Restarts..
    if (
        udB.get_key("UPDATE_ON_RESTART")
        and os.path.exists(".git")
        and ultroid_bot.run_in_loop(updater())[0]
    ):
        ultroid_bot.run_in_loop(bash("bash installer.sh"))

        os.execl(sys.executable, sys.executable, "-m", "pyUltroid")

    ultroid_bot.run_in_loop(startup_stuff())

    # Guard against None me (can happen in partial init failures)
    if ultroid_bot.me:
        ultroid_bot.me.phone = None

    if ultroid_bot.me and not ultroid_bot.me.bot:
        udB.set_key("OWNER_ID", ultroid_bot.uid)

    LOGS.info("Initialising...")

    # Initialising asst/pmbot/addons config

    ultroid_bot.loop.create_task(keep_redis_alive())

    pmbot = udB.get_key("PMBOT")
    manager = udB.get_key("MANAGER")

    addons = udB.get_key("ADDONS")
    if addons is None:
        addons = Var.ADDONS or os.path.exists("addons")
    elif isinstance(addons, str):
        addons = addons.lower() == "true"

    vcbot = udB.get_key("VCBOT") or Var.VCBOT
    if HOSTED_ON == "okteto":
        vcbot = False

    if HOSTED_ON == "termux" or udB.get_key("LITE_DEPLOY"):
        _plugins = "autocorrect autopic audiotools compressor forcesubscribe fedutils gdrive glitch instagram nsfwfilter nightmode pdftools profanityfilter writer youtube imagetools twitter games ytdl"
        udB.set_key("EXCLUDE_OFFICIAL", _plugins)
        udB.set_key("EXCLUDE_ADDONS", "imagetools nightmode nsfwfilter")
        udB.set_key("NO_JOIN_CHANNEL", "True")

    # Load Essential Plugins First
    load_other_plugins(addons=addons, pmbot=pmbot, manager=manager, vcbot=vcbot)

    async def background_tasks():
        # Heavy tasks moved to background
        await autopilot()
        # Efficiency: Start the Auto-Cleanup Worker (30m interval)
        try:
            from .fns.tools import async_cleanup_worker
            ultroid_bot.loop.create_task(async_cleanup_worker())
        except Exception as e:
            LOGS.error(f"Cleanup Integration Error: {e}")
        # Customize Ultroid Assistant...
        await customize()
        # Warm up bot ID cache for media_dl auto-listener (avoids get_me() per message)
        try:
            from assistant.media_dl import _init_bot_id_cache
            await _init_bot_id_cache()
        except Exception:
            pass
        # for channel plugins
        plugin_channels = udB.get_key("PLUGIN_CHANNEL")
        if plugin_channels:
            await plug(plugin_channels)
        # Send/Ignore Deploy Message..
        if not udB.get_key("LOG_OFF"):
            await ready()
        # Edit Restarting Message (if It's restarting)
        await WasItRestart(udB)
        try:
            cleanup_cache()
        except BaseException:
            pass
        LOGS.info("All Background Tasks Completed.")

    # Run heavy tasks in background
    ultroid_bot.loop.create_task(background_tasks())

    suc_msg = """
            ----------------------------------------------------------------------
                Ultroid is Online! (Background tasks are still running...)
            ----------------------------------------------------------------------
    """
    LOGS.info(
        f"Took {time_formatter((time.time() - start_time)*1000)} to start •ULTROID•"
    )
    LOGS.info(suc_msg)


if __name__ == "__main__":
    main()

    asst.run()
