# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/TeamUltroid/pyUltroid/blob/main/LICENSE>.

import asyncio
import math
import os
import re
import shlex
import sys
import time
from traceback import format_exc
from urllib.parse import unquote
from urllib.request import urlretrieve

from .. import run_as_module, ULTConfig

if run_as_module:
    from ..configs import Var


try:
    from aiohttp import ClientSession as aiohttp_client
except ImportError:
    aiohttp_client = None
    try:
        import requests
    except ImportError:
        requests = None

try:
    import heroku3
except ImportError:
    heroku3 = None

try:
    from git import Repo
    from git.exc import GitCommandError, InvalidGitRepositoryError, NoSuchPathError
except ImportError:
    Repo = None


import asyncio
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from functools import partial, wraps

from telethon.helpers import _maybe_await
from telethon.tl import types
from telethon.utils import get_display_name

from .._misc import CMD_HELP
from .._misc._wrappers import eod, eor
from ..exceptions import DependencyMissingError
from . import *

if run_as_module:
    from ..dB._core import ADDONS, HELP, LIST, LOADED

from ..version import ultroid_version
from .FastTelethon import download_file as downloadable
from .FastTelethon import upload_file as uploadable


_shared_executor = ThreadPoolExecutor(
    max_workers=max(multiprocessing.cpu_count() * 5, 4)
)


def run_async(function):
    @wraps(function)
    async def wrapper(*args, **kwargs):
        # asyncio.get_running_loop() is the correct call inside an async context.
        # get_event_loop() is deprecated in Python 3.10+ when called outside a loop.
        return await asyncio.get_running_loop().run_in_executor(
            _shared_executor,
            partial(function, *args, **kwargs),
        )

    return wrapper


# ~~~~~~~~~~~~~~~~~~~~ small funcs ~~~~~~~~~~~~~~~~~~~~ #


def make_mention(user, custom=None):
    if user.username:
        return f"@{user.username}"
    return inline_mention(user, custom=custom)


def inline_mention(user, custom=None, html=False):
    mention_text = get_display_name(user) or "Deleted Account" if not custom else custom
    if isinstance(user, types.User):
        if html:
            return f"<a href=tg://user?id={user.id}>{mention_text}</a>"
        return f"[{mention_text}](tg://user?id={user.id})"
    if isinstance(user, types.Channel) and user.username:
        if html:
            return f"<a href=https://t.me/{user.username}>{mention_text}</a>"
        return f"[{mention_text}](https://t.me/{user.username})"
    return mention_text


# ----------------- Load \\ Unloader ---------------- #


def un_plug(shortname):
    from .. import asst, ultroid_bot

    try:
        all_func = LOADED[shortname]
        for client in [ultroid_bot, asst]:
            for x, _ in client.list_event_handlers():
                if x in all_func:
                    client.remove_event_handler(x)
        del LOADED[shortname]
        del LIST[shortname]
        ADDONS.remove(shortname)
    except (ValueError, KeyError):
        name = f"addons.{shortname}"
        for client in [ultroid_bot, asst]:
            for i in reversed(range(len(client._event_builders))):
                ev, cb = client._event_builders[i]
                if cb.__module__ == name:
                    del client._event_builders[i]
                    try:
                        del LOADED[shortname]
                        del LIST[shortname]
                        ADDONS.remove(shortname)
                    except KeyError:
                        pass


if run_as_module:

    async def safeinstall(event):
        from .. import HNDLR
        from ..startup.utils import load_addons

        if not event.reply_to:
            return await eod(
                event, f"Please use `{HNDLR}install` as reply to a .py file."
            )
        ok = await eor(event, "`Installing...`")
        reply = await event.get_reply_message()
        if not (
            reply.media
            and hasattr(reply.media, "document")
            and reply.file.name
            and reply.file.name.endswith(".py")
        ):
            return await eod(ok, "`Please reply to any python plugin`")
        plug = reply.file.name.replace(".py", "")
        if plug in list(LOADED):
            return await eod(ok, f"Plugin `{plug}` is already installed.")
        sm = reply.file.name.replace("_", "-").replace("|", "-")
        dl = await reply.download_media(f"addons/{sm}")
        if event.text[9:] != "f":
            read = open(dl).read()
            for dan in KEEP_SAFE().All:
                if re.search(dan, read):
                    os.remove(dl)
                    return await ok.edit(
                        f"**Installation Aborted.**\n**Reason:** Occurance of `{dan}` in `{reply.file.name}`.\n\nIf you trust the provider and/or know what you're doing, use `{HNDLR}install f` to force install.",
                    )
        try:
            load_addons(dl)  # dl.split("/")[-1].replace(".py", ""))
        except Exception as e:
            os.remove(dl)
            LOGS.error(f"Plugin installation failed for '{dl}': {e}")
            return await eor(ok, f"**ERROR**\n\n`{format_exc()}`", time=30)
        plug = sm.replace(".py", "")
        if plug in HELP:
            output = "**Plugin** - `{}`\n".format(plug)
            for i in HELP[plug]:
                output += i
            output += "\n© @TeamUltroid"
            await eod(ok, f"✓ `Ultroid - Installed`: `{plug}` ✓\n\n{output}")
        elif plug in CMD_HELP:
            output = f"Plugin Name-{plug}\n\n✘ Commands Available-\n\n"
            output += str(CMD_HELP[plug])
            await eod(ok, f"✓ `Ultroid - Installed`: `{plug}` ✓\n\n{output}")
        else:
            try:
                x = f"Plugin Name-{plug}\n\n✘ Commands Available-\n\n"
                for d in LIST[plug]:
                    x += HNDLR + d + "\n"
                await eod(ok, f"✓ `Ultroid - Installed`: `{plug}` ✓\n\n`{x}`")
            except Exception:
                await eod(ok, f"✓ `Ultroid - Installed`: `{plug}` ✓")

    async def heroku_logs(event):
        """
        post heroku logs
        """
        from .. import LOGS

        xx = await eor(event, "`Processing...`")
        if not (Var.HEROKU_API and Var.HEROKU_APP_NAME):
            return await xx.edit(
                "Please set `HEROKU_APP_NAME` and `HEROKU_API` in vars."
            )
        try:
            app = (heroku3.from_key(Var.HEROKU_API)).app(Var.HEROKU_APP_NAME)
        except Exception as se:
            LOGS.warning(f"Heroku Logs fetch failed: {se}")
            return await xx.edit(
                "`HEROKU_API` and `HEROKU_APP_NAME` is wrong! Kindly re-check in config vars."
            )
        await xx.edit("`Downloading Logs...`")
        ok = app.get_log()
        with open("ultroid-heroku.log", "w") as log:
            log.write(ok)
        await event.client.send_file(
            event.chat_id,
            file="ultroid-heroku.log",
            thumb=ULTConfig.thumb,
            caption="**Ultroid Heroku Logs.**",
        )

        os.remove("ultroid-heroku.log")
        await xx.delete()

    async def def_logs(ult, file):
        await ult.respond(
            "**Ultroid Logs.**",
            file=file,
            thumb=ULTConfig.thumb,
        )

    async def updateme_requirements():
        """Update requirements.."""
        await bash(
            f"{sys.executable} -m pip install --no-cache-dir -r requirements.txt"
        )

    @run_async
    def gen_chlog(repo, diff):
        """Generate Changelogs..."""
        UPSTREAM_REPO_URL = (
            Repo().remotes[0].config_reader.get("url").replace(".git", "")
        )
        ac_br = repo.active_branch.name
        ch_log = tldr_log = ""
        ch = f"<b>Ultroid {ultroid_version} updates for <a href={UPSTREAM_REPO_URL}/tree/{ac_br}>[{ac_br}]</a>:</b>"
        ch_tl = f"Ultroid {ultroid_version} updates for {ac_br}:"
        d_form = "%d/%m/%y || %H:%M"
        for c in repo.iter_commits(diff):
            ch_log += f"\n\n💬 <b>{c.count()}</b> 🗓 <b>[{c.committed_datetime.strftime(d_form)}]</b>\n<b><a href={UPSTREAM_REPO_URL.rstrip('/')}/commit/{c}>[{c.summary}]</a></b> 👨‍💻 <code>{c.author}</code>"
            tldr_log += f"\n\n💬 {c.count()} 🗓 [{c.committed_datetime.strftime(d_form)}]\n[{c.summary}] 👨‍💻 {c.author}"
        if ch_log:
            return str(ch + ch_log), str(ch_tl + tldr_log)
        return ch_log, tldr_log


# --------------------------------------------------------------------- #


async def bash(cmd, run_code=0):
    """
    run any command in subprocess and get output or error."""
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    err = stderr.decode().strip() or None
    out = stdout.decode().strip()
    if not run_code and err:
        if match := re.match(r"\/bin\/sh: (.*): ?(\w+): not found", err):
            return out, f"{match.group(2).upper()}_NOT_FOUND"
    return out, err


# ---------------------------UPDATER-------------------------------- #
# Will add in class


async def updater():
    from .. import LOGS

    try:
        off_repo = Repo().remotes[0].config_reader.get("url").replace(".git", "")
    except Exception as er:
        LOGS.exception(er)
        return
    try:
        repo = Repo()
    except NoSuchPathError as error:
        LOGS.info(f"`directory {error} is not found`")
        Repo().__del__()
        return
    except GitCommandError as error:
        LOGS.info(f"`Early failure! {error}`")
        Repo().__del__()
        return
    except InvalidGitRepositoryError:
        repo = Repo.init()
        origin = repo.create_remote("upstream", off_repo)
        origin.fetch()
        repo.create_head("main", origin.refs.main)
        repo.heads.main.set_tracking_branch(origin.refs.main)
        repo.heads.main.checkout(True)
    ac_br = repo.active_branch.name
    repo.create_remote("upstream", off_repo) if "upstream" not in repo.remotes else None
    ups_rem = repo.remote("upstream")
    ups_rem.fetch(ac_br)
    changelog, tl_chnglog = await gen_chlog(repo, f"HEAD..upstream/{ac_br}")
    return bool(changelog)


# ----------------Fast Upload/Download----------------
# @1danish_00 @new-dev0 @buddhhu


async def uploader(file, name, taime, event, msg):
    with open(file, "rb") as f:
        result = await uploadable(
            client=event.client,
            file=f,
            filename=name,
            progress_callback=lambda d, t: asyncio.get_running_loop().create_task(
                progress(d, t, event, taime, msg)
            ),
        )
    return result


async def downloader(filename, file, event, taime, msg):
    with open(filename, "wb") as fk:
        result = await downloadable(
            client=event.client,
            location=file,
            out=fk,
            progress_callback=lambda d, t: asyncio.get_running_loop().create_task(
                progress(d, t, event, taime, msg)
            ),
        )
    return result


# ~~~~~~~~~~~~~~~Async Searcher~~~~~~~~~~~~~~~
# @buddhhu


async def async_searcher(
    url: str,
    post: bool = False,
    head: bool = False,
    headers: dict = None,
    evaluate=None,
    object: bool = False,
    re_json: bool = False,
    re_content: bool = False,
    *args,
    **kwargs,
):
    if aiohttp_client:
        async with aiohttp_client(headers=headers) as client:
            method = client.head if head else (client.post if post else client.get)
            data = await method(url, *args, **kwargs)
            if evaluate:
                return await evaluate(data)
            if re_json:
                return await data.json()
            if re_content:
                return await data.read()
            if head or object:
                return data
            return await data.text()
    # elif requests:
    #     method = requests.head if head else (requests.post if post else requests.get)
    #     data = method(url, headers=headers, *args, **kwargs)
    #     if re_json:
    #         return data.json()
    #     if re_content:
    #         return data.content
    #     if head or object:
    #         return data
    #     return data.text
    else:
        raise DependencyMissingError("install 'aiohttp' to use this.")


# ~~~~~~~~~~~~~~~~~~~~DDL Downloader~~~~~~~~~~~~~~~~~~~~
# @buddhhu @new-dev0


async def download_file(link, name, validate=False):
    """for files, without progress callback with aiohttp"""

    async def _download(content):
        if validate and "application/json" in content.headers.get("Content-Type"):
            return None, await content.json()
        with open(name, "wb") as file:
            file.write(await content.read())
        return name, ""

    return await async_searcher(link, evaluate=_download)


async def fast_download(download_url, filename=None, progress_callback=None):
    if not aiohttp_client:
        return await download_file(download_url, filename)[0], None
    async with aiohttp_client() as session:
        async with session.get(download_url, timeout=None) as response:
            if not filename:
                filename = unquote(download_url.rpartition("/")[-1])
            total_size = int(response.headers.get("content-length", 0)) or None
            downloaded_size = 0
            start_time = time.time()
            with open(filename, "wb") as f:
                async for chunk in response.content.iter_chunked(1024):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                    if progress_callback and total_size:
                        await _maybe_await(
                            progress_callback(downloaded_size, total_size)
                        )
            return filename, time.time() - start_time


# --------------------------Media Funcs-------------------------------- #


def mediainfo(media):
    xx = str((str(media)).split("(", maxsplit=1)[0])
    m = ""
    if xx == "MessageMediaDocument":
        mim = media.document.mime_type
        if mim == "application/x-tgsticker":
            m = "sticker animated"
        elif "image" in mim:
            if mim == "image/webp":
                m = "sticker"
            elif mim == "image/gif":
                m = "gif as doc"
            else:
                m = "pic as doc"
        elif "video" in mim:
            if "DocumentAttributeAnimated" in str(media):
                m = "gif"
            elif "DocumentAttributeVideo" in str(media):
                i = str(media.document.attributes[0])
                if "supports_streaming=True" in i:
                    m = "video"
                else:
                    m = "video as doc"
            else:
                m = "video"
        elif "audio" in mim:
            m = "audio"
        else:
            m = "document"
    elif xx == "MessageMediaPhoto":
        m = "pic"
    elif xx == "MessageMediaWebPage":
        m = "web"
    return m


# ------------------Some Small Funcs----------------


def time_formatter(milliseconds):
    if not milliseconds:
        return "0s"
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    weeks, days = divmod(days, 7)
    
    parts = []
    if weeks: parts.append(f"{weeks}w")
    if days: parts.append(f"{days}d")
    if hours: parts.append(f"{hours}h")
    if minutes: parts.append(f"{minutes}m")
    if seconds: parts.append(f"{seconds}s")
    
    return ":".join(parts) if parts else "0s"


def humanbytes(size):
    if not size:
        return "0 B"
    for unit in ["", "K", "M", "G", "T"]:
        if size < 1024:
            break
        size /= 1024
    if isinstance(size, int):
        size = f"{size}{unit}B"
    elif isinstance(size, float):
        size = f"{size:.2f}{unit}B"
    return size


def numerize(number):
    if not number:
        return None
    unit = ""
    for unit in ["", "K", "M", "B", "T"]:
        if number < 1000:
            break
        number /= 1000
    if isinstance(number, int):
        number = f"{number}{unit}"
    elif isinstance(number, float):
        number = f"{number:.2f}{unit}"
    return number


No_Flood = {}
_NO_FLOOD_PRUNE_THRESHOLD = 80


async def progress(current, total, event, start, type_of_ps, file_name=None, buttons=None):
    """Universal progress bar with button support and flood protection."""
    now = time.time()
    chat_id = event.chat_id
    msg_id = event.id

    # Lazy pruning: only scan and evict when the dict grows large.
    # Avoids O(n) scan on every call in normal operation.
    if len(No_Flood) > _NO_FLOOD_PRUNE_THRESHOLD:
        for c_id in list(No_Flood.keys()):
            for m_id in list(No_Flood[c_id].keys()):
                if now - No_Flood[c_id][m_id] > 30:
                    del No_Flood[c_id][m_id]
            if not No_Flood[c_id]:
                del No_Flood[c_id]

    if chat_id in No_Flood:
        if msg_id in No_Flood[chat_id]:
            if (now - No_Flood[chat_id][msg_id]) < 1.1:
                return
        No_Flood[chat_id][msg_id] = now
    else:
        No_Flood[chat_id] = {msg_id: now}

    diff = now - start
    percentage = current * 100 / total
    speed = current / diff if diff > 0 else 0
    eta = round((total - current) / speed) * 1000 if speed > 0 else 0

    filled = math.floor(percentage / 5)
    progress_str = f"`[{'●' * filled}{' ' * (20 - filled)}] {percentage:.2f}%`"

    tmp = (
        f"{progress_str}\n\n"
        f"`{humanbytes(current)} of {humanbytes(total)}`\n\n"
        f"`✦ Speed: {humanbytes(speed)}/s`\n\n"
        f"`✦ ETA: {time_formatter(eta)}`"
    )
    caption = f"`✦ {type_of_ps}`\n\n"
    if file_name:
        caption += f"`File Name: {file_name}`\n\n"
    await event.edit(caption + tmp, buttons=buttons)


# ------------------System\\Heroku stuff----------------
# @xditya @sppidy @techierror


async def restart(ult=None):
    if Var.HEROKU_APP_NAME and Var.HEROKU_API:
        try:
            Heroku = heroku3.from_key(Var.HEROKU_API)
            app = Heroku.apps()[Var.HEROKU_APP_NAME]
            if ult:
                await ult.edit("`Restarting your app, please wait for a minute!`")
            app.restart()
        except BaseException as er:
            if ult:
                return await eor(
                    ult,
                    "`HEROKU_API` or `HEROKU_APP_NAME` is wrong! Kindly re-check in config vars.",
                )
            LOGS.exception(er)
    else:
        args = [sys.executable, "-m", "pyUltroid"] + sys.argv[1:]
        os.execl(sys.executable, *args)


async def shutdown(ult):
    from .. import HOSTED_ON, LOGS

    ult = await eor(ult, "Shutting Down")
    if HOSTED_ON == "heroku":
        if not (Var.HEROKU_APP_NAME and Var.HEROKU_API):
            return await ult.edit("Please Fill `HEROKU_APP_NAME` and `HEROKU_API`")
        dynotype = os.getenv("DYNO").split(".")[0]
        try:
            Heroku = heroku3.from_key(Var.HEROKU_API)
            app = Heroku.apps()[Var.HEROKU_APP_NAME]
            await ult.edit("`Shutting Down your app, please wait for a minute!`")
            app.process_formation()[dynotype].scale(0)
        except BaseException as e:
            LOGS.exception(e)
            return await ult.edit(
                "`HEROKU_API` and `HEROKU_APP_NAME` is wrong! Kindly re-check in config vars."
            )

async def catbox_upload(path: str):
    """
    Safely upload a file to Catbox with size validation (200MB limit).
    Returns the URL on success, or raises an exception with a clear message.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")

    size = os.path.getsize(path)
    # Catbox has a strict 200MB limit for guest uploads.
    if size > 200 * 1024 * 1024:
        raise ValueError(f"File too large ({humanbytes(size)}). Catbox guest limit is 200MB.")

    async def upload_to_service(url, session, field_name, file_path):
        clean_name = re.sub(r'[^a-zA-Z0-9._]', '_', os.path.basename(file_path))
        # Browser-like headers to avoid being blocked
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        with open(file_path, "rb") as f:
            data = aiohttp.FormData()
            if "catbox.moe" in url:
                data.add_field("reqtype", "fileupload")
                data.add_field("fileToUpload", f, filename=clean_name)
            elif "uguu.se" in url:
                data.add_field("files[]", f, filename=clean_name)
            else:
                data.add_field(field_name, f, filename=clean_name)

            try:
                async with session.post(url, data=data, headers=headers, timeout=30) as resp:
                    text = await resp.text()
                    if text.startswith("https://"):
                        return text.strip()
                    try:
                        res = json.loads(text)
                        if isinstance(res, list) and res and res[0].get("src"):
                            base_url = "https://graph.org" if "graph.org" in url else "https://telegra.ph"
                            return base_url + res[0]["src"]
                        if isinstance(res, dict):
                            if res.get("success") and res.get("files"): # Uguu.se format
                                return res["files"][0]["url"]
                            if res.get("error"):
                                return res["error"]
                    except:
                        pass
                    return text[:100] or "Unknown Error"
            except Exception as e:
                return str(e)

    try:
        import aiohttp
        import json
        from .. import LOGS
        async with aiohttp.ClientSession() as session:
            # 1. Uguu.se (Very reliable for blocked IPs)
            res_u = await upload_to_service("https://uguu.se/upload.php", session, "files[]", path)
            if res_u.startswith("https://"): return res_u

            # 2. Catbox
            LOGS.warning(f"Uguu failed ({res_u}). Trying Catbox...")
            res = await upload_to_service("https://catbox.moe/user/api.php", session, "fileToUpload", path)
            if res.startswith("https://"): return res
            
            # 3. Telegra.ph
            LOGS.warning(f"Catbox failed ({res}). Trying Telegra.ph...")
            res2 = await upload_to_service("https://telegra.ph/upload", session, "file", path)
            if res2.startswith("https://"): return res2
            
            raise Exception(f"All services failed. Uguu: {res_u}, Catbox: {res}, Telegra: {res2}")
    except Exception as e:
        raise Exception(f"Upload process failed: {str(e)}") from e

def time_cache(ttl=60):
    """
    Unified Command Caching
    Memoizes function results for `ttl` seconds to reduce CPU/IO load.
    Use for expensive system calls or repeated DB queries.
    """
    def decorator(func):
        cache = {}
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            now = time.time()
            if key in cache:
                result, timestamp = cache[key]
                if now - timestamp < ttl:
                    return result
            # Assuming the function is either async or sync
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            cache[key] = (result, now)
            return result
        return async_wrapper
    return decorator


async def aexec(code, event):
    """
    Async execution for code blocks — used internally by helper utilities.
    For eval command execution, the authoritative version is in devtools.py.
    """
    exec_globals = {
        'asyncio': asyncio,
        'os': os,
        'sys': sys,
        'time': time,
        'event': event,
        'client': event.client,
        'reply': await event.get_reply_message(),
        'chat': event.chat_id,
        '__builtins__': __builtins__,
    }

    wrapped_code = f"async def __aexec(e, client):\n" + "".join(f"    {line}\n" for line in code.split("\n"))

    try:
        exec(wrapped_code, exec_globals)
        return await exec_globals["__aexec"](event, event.client)
    except Exception:
        return format_exc()
