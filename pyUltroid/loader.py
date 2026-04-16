# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/TeamUltroid/pyUltroid/blob/main/LICENSE>.

import contextlib
import glob
import os
from importlib import import_module
from logging import Logger

from . import LOGS
from .fns.tools import get_all_files


class Loader:
    def __init__(self, path="plugins", key="Official", logger: Logger = LOGS):
        self.path = path
        self.key = key
        self._logger = logger

    def load(
        self,
        log=True,
        func=import_module,
        include=None,
        exclude=None,
        after_load=None,
        load_all=False,
    ):
        files = []
        if os.path.isfile(self.path):
            files = [self.path]
        elif include:
            if log:
                self._logger.info("Including: {}".format("• ".join(include)))
            # Load only required files
            for file in include:
                path = f"{self.path}/{file}.py"
                if os.path.exists(path):
                    files.append(path)
            # Add hidden/internal files
            files.extend(glob.glob(f"{self.path}/_*.py"))
        else:
            if load_all:
                files = get_all_files(self.path, ".py")
            else:
                with os.scandir(self.path) as it:
                    for entry in it:
                        if entry.is_file() and entry.name.endswith(".py") and not entry.name.startswith("__"):
                            files.append(entry.path)
            
            if exclude:
                exclude_set = {f"{self.path}/{x}.py" for x in exclude if not x.startswith("_")}
                files = [f for f in files if f not in exclude_set]

        if log and files:
            self._logger.info(
                f"• Installing {self.key} Plugins || Count : {len(files)} •"
            )
        
        for plugin in sorted(files):
            if func == import_module:
                plugin = plugin.replace(".py", "").replace("/", ".").replace("\\", ".")
            try:
                modl = func(plugin)
            except ModuleNotFoundError:
                continue
            except Exception as exc:
                self._logger.error(f"pyUltroid - {self.key} - ERROR - {plugin}: {exc}")
                continue
            
            if callable(after_load):
                p_name = plugin.split(".")[-1] if func == import_module else plugin
                after_load(self, modl, plugin_name=p_name)
