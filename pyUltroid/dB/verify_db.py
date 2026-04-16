# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/TeamUltroid/pyUltroid/blob/main/LICENSE>.

from .base import KeyManager

# Persistent list of verified User IDs (Level 1: Verification Click)
VerifiedUsers = KeyManager("ASSISTANT_VERIFIED_USERS", cast=list)

# Persistent list of users who passed Logic Challenge (Level 2: Captcha)
CaptchaVerified = KeyManager("ASSISTANT_CAPTCHA_VERIFIED", cast=list)

# Usage Logs for Rate Limiting
UsageLogs = KeyManager("ASSISTANT_USAGE_LOGS", cast=dict)

def is_verified(user_id: int) -> bool:
    """Check if a specific user has passed Level 1 (Identity Verify)."""
    return VerifiedUsers.contains(user_id)

def is_fully_authorized(user_id: int) -> bool:
    """Check if a user has passed Level 2 (Logic Challenge)."""
    return CaptchaVerified.contains(user_id)

def add_captcha_verified(user_id: int):
    """Register user after passing the Logic Challenge."""
    CaptchaVerified.add(user_id)

def add_verified(user_id: int):
    """Add a user to the persistent verified list."""
    VerifiedUsers.add(user_id)

def remove_verified(user_id: int):
    """Revoke verification from a user."""
    VerifiedUsers.remove(user_id)
