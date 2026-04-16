# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/TeamUltroid/pyUltroid/blob/main/LICENSE>.

from .base import KeyManager

# Persistent list of verified User IDs
VerifiedUsers = KeyManager("ASSISTANT_VERIFIED_USERS", cast=list)

def is_verified(user_id: int) -> bool:
    """Check if a specific user has passed the identity audit."""
    return VerifiedUsers.contains(user_id)

def add_verified(user_id: int):
    """Add a user to the persistent verified list."""
    VerifiedUsers.add(user_id)

def remove_verified(user_id: int):
    """Revoke verification from a user."""
    VerifiedUsers.remove(user_id)
