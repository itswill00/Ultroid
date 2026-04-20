from . import get_help
__doc__ = get_help("help_animation")
import asyncio
from pyUltroid.base import ultroid_cmd

@ultroid_cmd(pattern="headshot$")
async def headshot(e):
    animation_interval = 0.2
    animation_ttl = range(0, 11)
    a = await e.eor("...")
    animation_chars = [
        "(·_· )",
        "( o_o)",
        "( O_O)",
        "(O_O )",
        "( -_-)",
        "(  -_-)?",
        "( •_•)",
        "( •_•)>⌐■-■",
        "(⌐■_■)",
        "逐",
        " "
    ]
    for i in animation_ttl:
        await asyncio.sleep(animation_interval)
        await a.edit(animation_chars[i % 11])
    await a.edit("`Targeted user killed by Headshot\ud83d\ude08.\ud83d\ude08.\ud83d\ude08.\ud83d\ude08.\ud83d\ude08.\ud83d\ude08.\ud83d\ude08......`" + "\n" + "`#Sad_Reacts_Offline`")

@ultroid_cmd(pattern="fbi$")
async def fbi(e):
    animation_interval = 0.2
    animation_chars = [
        "(·_· )",
        "( o_o)",
        "( O_O)",
        "(O_O )",
        "( -_-)",
        "(  -_-)?",
        "( •_•)",
        "( •_•)>⌐■-■",
        "(⌐■_■)",
        "FBI OPEN UP !!!!!"
    ]
    a = await e.eor("...")
    for char in animation_chars:
        await asyncio.sleep(animation_interval)
        await a.edit(char)

    await a.edit("`The target has been terminated by the FBI! \ud83d\ude08\ud83d\ude08\ud83d\ude08`" + "\n" + "`#FBI_Open_Up`")

@ultroid_cmd(pattern="fp$")
async def fp(e):
    await e.eor("\ud83e\udd26\u200d\u2642")

__doc__ = get_help("help_animation")
