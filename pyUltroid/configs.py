# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/TeamUltroid/pyUltroid/blob/main/LICENSE>.

import sys

from decouple import config

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def _env(key, default=None, cast=None):
    """
    Safe wrapper around decouple.config().
    Treats empty string values as if the key was not set (falls back to default).
    Catches cast errors (e.g. int('')) gracefully — prevents crash when
    .env has keys set to empty string (e.g. API_ID=).
    """
    try:
        raw = config(key, default=None)
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            return default
        if cast:
            return cast(raw.strip())
        return raw.strip() if isinstance(raw, str) else raw
    except (ValueError, TypeError):
        return default


class Var:
    # mandatory
    API_ID = (
        int(sys.argv[1]) if len(sys.argv) > 1 else _env("API_ID", default=6, cast=int)
    )
    API_HASH = (
        sys.argv[2]
        if len(sys.argv) > 2
        else _env("API_HASH", default="eb06d4abfb49dc3eeb1aeb98ae0f581e")
    )
    SESSION = sys.argv[3] if len(sys.argv) > 3 else _env("SESSION", default=None)
    REDIS_URI = (
        sys.argv[4]
        if len(sys.argv) > 4
        else (_env("REDIS_URI", default=None) or _env("REDIS_URL", default=None))
    )
    REDIS_PASSWORD = (
        sys.argv[5] if len(sys.argv) > 5 else _env("REDIS_PASSWORD", default=None)
    )
    # extras
    BOT_TOKEN = _env("BOT_TOKEN", default=None)
    LOG_CHANNEL = _env("LOG_CHANNEL", default=0, cast=int)
    HEROKU_APP_NAME = _env("HEROKU_APP_NAME", default=None)
    HEROKU_API = _env("HEROKU_API", default=None)
    VC_SESSION = _env("VC_SESSION", default=None)
    ADDONS = _env("ADDONS", default=False, cast=lambda v: v.lower() in ("true", "1", "yes"))
    VCBOT = _env("VCBOT", default=False, cast=lambda v: v.lower() in ("true", "1", "yes"))
    # for railway
    REDISPASSWORD = _env("REDISPASSWORD", default=None)
    REDISHOST = _env("REDISHOST", default=None)
    REDISPORT = _env("REDISPORT", default=None)
    REDISUSER = _env("REDISUSER", default=None)
    # for sql
    DATABASE_URL = _env("DATABASE_URL", default=None)
    # for MONGODB users
    MONGO_URI = _env("MONGO_URI", default=None)
    # extra
    TGDB_URL = _env("TGDB_URL", default=None)
    # runtime mode: "user" | "bot" | "dual" (default: "dual")
    # user  → userbot only, no separate assistant bot
    # bot   → bot only via BOT_TOKEN, no SESSION userbot
    # dual  → both userbot + assistant bot active (classic Ultroid)
    RUNTIME_MODE = _env("RUNTIME_MODE", default="")
