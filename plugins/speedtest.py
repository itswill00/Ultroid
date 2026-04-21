# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

from . import get_help

__doc__ = get_help("speedtest")

"""
» Commands Available -

• `{i}speedtest`
    Standard speed test (text).

• `{i}speedtest image`
    Speed test with official graphic result.
"""

import asyncio
from datetime import datetime

from pyUltroid import asst
from . import HOSTED_ON, LOGS, Button, asst_cmd, humanbytes, ultroid_cmd

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
    x = await ult.eor("`Establishing connection to the nearest node...`")

    try:
        # Step 1: Initialize
        asyncio.get_running_loop()
        s = speedtest.Speedtest()

        await x.edit("`Selecting the optimal service node...`")
        best = await asyncio.to_thread(s.get_best_server)

        # Step 2: Download
        await x.edit(f"`Measuring download throughput...` \n<b>Node:</b> <code>{best['sponsor']} ({best['name']})</code>", parse_mode="html")
        await asyncio.to_thread(s.download)

        # Step 3: Upload
        await x.edit(f"`Measuring upload throughput...` \n<b>Latency:</b> <code>{s.results.ping:.2f} ms</code>", parse_mode="html")
        await asyncio.to_thread(s.upload)

        # Step 4: Finalize
        if "image" in match:
            await x.edit("`Gathering the final results...`")
            share_url = await asyncio.to_thread(s.results.share)

        res = s.results.dict()

        # UI Formatting (Ultra-Premium Dashboard)
        down = humanbytes(res['download'] / 8) + "/s"
        up = humanbytes(res['upload'] / 8) + "/s"
        isp = res['client']['isp']
        server = f"{res['server']['sponsor']} ({res['server']['name']})"
        ping = f"{res['ping']:.2f} ms"

        text = (
            f"<b>Network Statistics</b>\n"
            f"───\n"
            f"📡 <b>ISP:</b> <code>{isp}</code>\n"
            f"📍 <b>Node:</b> <code>{server}</code>\n"
            f"───\n"
            f"📥 <b>Download:</b> <code>{down}</code>\n"
            f"📤 <b>Upload:</b> <code>{up}</code>\n"
            f"⏳ <b>Latency:</b> <code>{ping}</code>\n"
            f"───\n"
            f"<i>Verified on my Private VPS at {datetime.now().strftime('%H:%M %Z')}</i>"
        )

        buttons = [
            [
                Button.inline("Re-Test", data="speedtest"),
                Button.inline("Stats", data="alive")
            ],
            [Button.inline("✕ Close", data="close")]
        ] if getattr(asst, "_bot", False) else None

        if "image" in match and share_url:
            await asst.send_file(
                ult.chat_id,
                file=share_url,
                caption=text,
                parse_mode="html",
                buttons=buttons,
                reply_to=ult.id
            )
            await x.delete()
        else:
            await asst.send_message(
                ult.chat_id,
                text,
                parse_mode="html",
                buttons=buttons,
                reply_to=ult.id
            )
            await x.delete()

    except Exception as e:
        LOGS.exception(e)
        await x.edit(f"**[ ❌ ] Speedtest Error:**\n`{str(e)}`")
