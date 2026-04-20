# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.
"""
» Commands Available -

• `{i}speedtest`
    Standard speed test (text).

• `{i}speedtest image`
    Speed test with official graphic result.
"""

import asyncio
from datetime import datetime

from . import HOSTED_ON, LOGS, asst_cmd, humanbytes, ultroid_cmd

try:
    import speedtest
except ImportError:
    speedtest = None

# ── Speedtest Engine (Asynchronous Wrapper) ──────────────────

def _run_speedtest(use_image=False):
    """Execution logic in a separate thread."""
    if not speedtest:
        return {"error": "'speedtest-cli' package is missing. Install it: pip install speedtest-cli"}

    try:
        s = speedtest.Speedtest()
        s.get_best_server()
        s.download()
        s.upload()
        if use_image:
            s.results.share()
        return s.results.dict()
    except Exception as e:
        return {"error": str(e)}


@asst_cmd(pattern="speedtest")
@ultroid_cmd(pattern="speedtest( (.*)|$)")
async def turbo_speedtest(ult):
    # Try dynamic import to allow detection without restart
    try:
        import speedtest
    except ImportError:
        return await ult.eor(
            "`'speedtest-cli' package not found!`\n\n"
            "**Fix:**\n"
            "1. Run: `pip install speedtest-cli` in your terminal.\n"
            "2. Restart the bot."
        )

    try:
        match = ult.pattern_match.group(1).strip().lower()
    except (IndexError, AttributeError):
        match = ""
    x = await ult.eor("`Measuring network performance...`")

    try:
        # Step 1: Initialize
        loop = asyncio.get_running_loop()
        s = speedtest.Speedtest()

        await x.edit("`Selecting optimal service node...`")
        best = await asyncio.to_thread(s.get_best_server)

        # Step 2: Download
        await x.edit(f"`Measuring download throughput...` \n**Node:** `{best['sponsor']} ({best['name']})`")
        await asyncio.to_thread(s.download)

        # Step 3: Upload
        await x.edit("`Measuring upload throughput...` \n**Latency:** `{:.2f} ms`".format(s.results.ping))
        await asyncio.to_thread(s.upload)

        # Step 4: Finalize
        if "image" in match:
            await x.edit("`Exporting diagnostic report...`")
            share_url = await asyncio.to_thread(s.results.share)

        res = s.results.dict()

        # UI Formatting (Professional & Neutral)
        down = humanbytes(res['download'] / 8) + "/s"
        up = humanbytes(res['upload'] / 8) + "/s"
        isp = res['client']['isp']
        server = f"{res['server']['sponsor']} ({res['server']['name']})"
        ping = f"{res['ping']:.2f} ms"

        text = (
            f"**Network Statistics**\n"
            f"---"
            f"\n**Service Provider:** `{isp}`"
            f"\n**Assigned Node:** `{server}`"
            f"\n---"
            f"\n**Download:** `{down}`"
            f"\n**Upload:** `{up}`"
            f"\n**Latency:** `{ping}`"
            f"\n---"
            f"\n⚙️ `{HOSTED_ON}` | `{datetime.now().strftime('%H:%M %Z')}`"
        )

        if "image" in match and share_url:
            await ult.client.send_file(
                ult.chat_id,
                file=share_url,
                caption=text,
                reply_to=ult.id
            )
            await x.delete()
        else:
            await x.edit(text)

    except Exception as e:
        LOGS.exception(e)
        await x.edit(f"**[ ❌ ] Speedtest Error:**\n`{str(e)}`")

