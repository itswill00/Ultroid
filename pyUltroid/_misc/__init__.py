# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/TeamUltroid/pyUltroid/blob/main/LICENSE>.


from .. import *

CMD_HELP = {}
# ----------------------------------------------#


class _SudoManager:
    def __init__(self):
        self.db = None
        self._owner = None
        self._sudos = None
        self._fullsudos = None
        self._scoped_sudos = None
        self._should_allow_sudo = None

    def _init_db(self):
        if not self.db:
            from .. import udB
            self.db = udB
        return self.db

    def get_sudos(self):
        if self._sudos is not None:
            return self._sudos
        db = self._init_db()
        sudos = db.get_key("SUDOS") or []
        if isinstance(sudos, str):
            sudos = [x for x in sudos.split()]

        # Robust integer casting
        cleaned = []
        for x in sudos:
            try:
                cleaned.append(int(x))
            except (ValueError, TypeError):
                continue
        self._sudos = cleaned
        return self._sudos


    def get_scoped_sudos(self):
        if self._scoped_sudos is not None:
            return self._scoped_sudos
        db = self._init_db()
        scoped = db.get_key("SUDO_SCOPE") or {}
        # Ensure it's a dict {user_id: [cmds]}
        if isinstance(scoped, str):
            import json
            try:
                scoped = json.loads(scoped)
            except Exception:
                scoped = {}
        # Ensure all keys are strings (for JSON compatibility) but we want ints in memory
        self._scoped_sudos = {int(k): v for k, v in scoped.items()}
        return self._scoped_sudos

    @property
    def owner(self):
        if self._owner is not None:
            return self._owner
        db = self._init_db()
        oid = db.get_key("OWNER_ID")
        try:
            self._owner = int(oid) if oid else None
        except (ValueError, TypeError):
            self._owner = None
        return self._owner

    @property
    def should_allow_sudo(self):

        if self._should_allow_sudo is not None:
            return self._should_allow_sudo
        db = self._init_db()
        val = db.get_key("SUDO")
        # Ensure it handles 'True/False/1/0' correctly from DB
        if isinstance(val, str):
            self._should_allow_sudo = val.lower() in ("true", "1", "yes")
        else:
            self._should_allow_sudo = bool(val)
        return self._should_allow_sudo

    def owner_and_sudos(self):
        return [self.owner, *self.get_sudos()] if self.owner else self.get_sudos()


    @property
    def fullsudos(self):
        if self._fullsudos is not None:
            return self._fullsudos
        db = self._init_db()
        fsudos = db.get_key("FULLSUDO") or []
        if isinstance(fsudos, str):
            fsudos = fsudos.split()

        # Ensure all IDs are integers
        cleaned_fs = []
        for x in fsudos:
            try:
                cleaned_fs.append(int(x))
            except (ValueError, TypeError):
                continue

        # Combine with owner
        if self.owner and self.owner not in cleaned_fs:
            cleaned_fs.append(self.owner)

        self._fullsudos = cleaned_fs
        return self._fullsudos


    def is_sudo(self, id_):
        return id_ in self.get_sudos()

    def is_authorized(self, sender_id: int, pattern: str) -> bool:
        """Determines if a user has permission to execute a specific command."""
        # 1. Owner & Full Sudoers have absolute access
        if sender_id in self.fullsudos:
            return True

        # 2. Check standard sudoers
        if sender_id not in self.get_sudos():
            return False

        # 3. Check scope (Granular Control)
        scopes = self.get_scoped_sudos()
        if sender_id not in scopes:
            # Standard sudoer with no scope = Global Sudo (historical behavior)
            return True

        # Extract cmd name from pattern
        cmd_name = None
        import re
        p_str = pattern.pattern if hasattr(pattern, "pattern") else str(pattern)
        # Match alphanumeric word (cmd name) after common prefix characters
        match = re.search(r"[a-zA-Z0-9_]+", p_str.replace("\\", ""))
        if match:
            cmd_name = match.group(0).lower()

        # If we can't extract a name, allow for safety or block?
        # Blocking is safer but might break weird patterns.
        if not cmd_name:
            return True

        allowed = scopes[sender_id]
        if isinstance(allowed, str):
            allowed = [allowed]

        # Check against allowed list
        return cmd_name in [c.lower() for c in allowed]

    def refresh(self):
        self._sudos = None
        self._fullsudos = None
        self._scoped_sudos = None
        self._should_allow_sudo = None
        self._owner = None


class _ConfigCache:
    def __init__(self):
        self._cache = {}

    def get(self, key, default=None):
        if key in self._cache:
            return self._cache[key]
        from .. import udB
        val = udB.get_key(key)
        if val is not None:
            self._cache[key] = val
        return val if val is not None else default

    def refresh(self):
        self._cache.clear()


SUDO_M = _SudoManager()
ULT_CONFIG = _ConfigCache()
owner_and_sudos = SUDO_M.owner_and_sudos
sudoers = SUDO_M.get_sudos
is_sudo = SUDO_M.is_sudo


def refresh_all():
    SUDO_M.refresh()
    ULT_CONFIG.refresh()

# ------------------------------------------------ #


def append_or_update(load, func, name, arggs):
    if isinstance(load, list):
        return load.append(func)
    if isinstance(load, dict):
        if load.get(name):
            return load[name].append((func, arggs))
        return load.update({name: [(func, arggs)]})
