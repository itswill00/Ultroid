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
        self._sudos = db.get_key("SUDOS") or []
        return self._sudos

    @property
    def should_allow_sudo(self):
        if self._should_allow_sudo is not None:
            return self._should_allow_sudo
        db = self._init_db()
        self._should_allow_sudo = db.get_key("SUDO")
        return self._should_allow_sudo

    def owner_and_sudos(self):
        if not self._owner:
            db = self._init_db()
            self._owner = db.get_key("OWNER_ID")
        return [self._owner, *self.get_sudos()]

    @property
    def fullsudos(self):
        if self._fullsudos is not None:
            return self._fullsudos
        db = self._init_db()
        fsudos = db.get_key("FULLSUDO")
        if not self._owner:
            self._owner = db.get_key("OWNER_ID")
        if not fsudos:
            self._fullsudos = [self._owner]
            return self._fullsudos
        if isinstance(fsudos, str):
            fsudos = [int(_) for _ in fsudos.split()]
        elif isinstance(fsudos, list):
            fsudos = [int(_) for _ in fsudos]
        else:
            fsudos = []
        if self._owner and self._owner not in fsudos:
            fsudos.append(self._owner)
        self._fullsudos = fsudos
        return self._fullsudos

    def is_sudo(self, id_):
        return id_ in self.get_sudos()

    def refresh(self):
        self._sudos = None
        self._fullsudos = None
        self._should_allow_sudo = None
        self._owner = None


SUDO_M = _SudoManager()
owner_and_sudos = SUDO_M.owner_and_sudos
sudoers = SUDO_M.get_sudos
is_sudo = SUDO_M.is_sudo

# ------------------------------------------------ #


def append_or_update(load, func, name, arggs):
    if isinstance(load, list):
        return load.append(func)
    if isinstance(load, dict):
        if load.get(name):
            return load[name].append((func, arggs))
        return load.update({name: [(func, arggs)]})
