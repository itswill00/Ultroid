# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/TeamUltroid/pyUltroid/blob/main/LICENSE>.

class KEEP_SAFE:
    """
    Security patterns to scan for malicious or sensitive information
    in plugins or dynamic execution.
    """
    def __init__(self):
        # Professional-grade patterns to match sensitive data and dangerous operations
        self.All = [
            # Sensitive Credentials (Case Insensitive)
            r"(?i)SESSION",
            r"(?i)API_ID",
            r"(?i)API_HASH",
            r"(?i)BOT_TOKEN",
            r"(?i)MONGO_URI",
            r"(?i)REDIS_URI",
            r"(?i)REDISHOST",
            r"(?i)DATABASE_URL",
            r"(?i)DYNO", # Heroku specific

            # Destructive Shell Operations
            r"rm -rf",
            r"mkfs",
            r":\(\)\{ :\|:& \};:", # Fork bomb
            r"mv / .* /dev/null",
            r"> /dev/sda",

            # Potential Information Leakage
            r"os\.environ",
            r"getattr\(Var",
        ]
