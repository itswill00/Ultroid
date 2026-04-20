"""
» Commands Available -

• `{i}addons <on/off>`
    Enable or disable the loading of external addons. 
    Enabling addons allows the bot to load plugins from the `addons/` directory upon restart.
"""
from . import udB, ultroid_cmd


@ultroid_cmd(pattern="addons (on|off)$", fullsudo=True)
async def toggle_addons(e):
    choice = e.pattern_match.group(1)
    if choice == "on":
        if udB.get_key("ADDONS"):
            return await e.eor("`Addons are already ENABLED.`", time=5)
        udB.set_key("ADDONS", "True")
        await e.eor("`Addons have been ENABLED. Restarting to load addons...`", time=5)
    else:
        if not udB.get_key("ADDONS"):
            return await e.eor("`Addons are already DISABLED.`", time=5)
        udB.set_key("ADDONS", "False")
        await e.eor("`Addons have been DISABLED. Restarting to apply changes...`", time=5)

    # Trigger restart directly — no Telegram round-trip needed
    import json as _json
    import os
    import sys
    import time as _time
    udB.set_key("_RESTART", _json.dumps({
        "who": "user",
        "chat_id": e.chat_id,
        "msg_id": e.id,
        "ts": _time.time(),
        "version": udB.get_key("ULTROID_VERSION") or "?",
    }))
    args = [sys.executable, "-m", "pyUltroid"] + sys.argv[1:]
    os.execl(sys.executable, *args)
