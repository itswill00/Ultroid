# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/TeamUltroid/pyUltroid/blob/main/LICENSE>.

import math
import time
from io import FileIO
from logging import WARNING
from mimetypes import guess_type

from apiclient.http import LOGGER, MediaFileUpload, MediaIoBaseDownload
from googleapiclient.discovery import build, logger
from httplib2 import Http
from oauth2client.client import OOB_CALLBACK_URN, OAuth2WebServerFlow
from oauth2client.client import logger as _logger
from oauth2client.file import Storage

from .. import udB
from .helper import (
    _NO_FLOOD_PRUNE_THRESHOLD,
    No_Flood,
    humanbytes,
    run_async,
    time_formatter,
)

for log in [LOGGER, logger, _logger]:
    log.setLevel(WARNING)


class GDriveManager:
    def __init__(self):
        self._flow = {}
        self.gdrive_creds = {
            "oauth_scope": [
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/drive.file",
                "https://www.googleapis.com/auth/drive.metadata",
            ],
            "dir_mimetype": "application/vnd.google-apps.folder",
            "redirect_uri": OOB_CALLBACK_URN,
        }
        self.auth_token = udB.get_key("GDRIVE_AUTH_TOKEN")
        self.folder_id = udB.get_key("GDRIVE_FOLDER_ID")
        self.token_file = "resources/auth/gdrive_creds.json"

    @staticmethod
    def _create_download_link(fileId: str):
        return f"https://drive.google.com/uc?id={fileId}&export=download"

    @staticmethod
    def _create_folder_link(folderId: str):
        return f"https://drive.google.com/folderview?id={folderId}"

    def _create_token_file(self, code: str = None):
        if code and self._flow:
            _auth_flow = self._flow["_"]
            credentials = _auth_flow.step2_exchange(code)
            Storage(self.token_file).put(credentials)
            return udB.set_key("GDRIVE_AUTH_TOKEN", str(open(self.token_file).read()))
        try:
            _auth_flow = OAuth2WebServerFlow(
                udB.get_key("GDRIVE_CLIENT_ID")
                or "458306970678-jhfbv6o5sf1ar63o1ohp4c0grblp8qba.apps.googleusercontent.com",
                udB.get_key("GDRIVE_CLIENT_SECRET")
                or "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",
                self.gdrive_creds["oauth_scope"],
                redirect_uri=self.gdrive_creds["redirect_uri"],
            )
            self._flow["_"] = _auth_flow
        except KeyError:
            return "Fill GDRIVE client credentials"
        return _auth_flow.step1_get_authorize_url()

    @property
    def _http(self):
        storage = Storage(self.token_file)
        creds = storage.get()
        http = Http()
        http.redirect_codes = http.redirect_codes - {308}
        creds.refresh(http)
        return creds.authorize(http)

    @property
    def _build(self):
        return build("drive", "v2", http=self._http, cache_discovery=False)

    async def _set_permissions(self, fileId: str):
        _permissions = {
            "role": "reader",
            "type": "anyone",
            "value": None,
            "withLink": True,
        }
        # execute() is blocking, must run in thread
        await run_async(self._build.permissions().insert(
            fileId=fileId, body=_permissions, supportsAllDrives=True
        ).execute)(http=self._http)

    async def _upload_file(
        self, event, path: str, filename: str = None, folder_id: str = None
    ):
        if not filename:
            filename = path.split("/")[-1]
        mime_type = guess_type(path)[0] or "application/octet-stream"

        # 25MB chunksize optimized for high-speed VPS bandwidth saturation
        media_body = MediaFileUpload(path, mimetype=mime_type, resumable=True, chunksize=25*1024*1024)
        body = {
            "title": filename,
            "description": "Uploaded using Ultroid Userbot",
            "mimeType": mime_type,
        }
        if folder_id:
            body["parents"] = [{"id": folder_id}]
        elif self.folder_id:
            body["parents"] = [{"id": self.folder_id}]

        insert_op = self._build.files().insert(
            body=body, media_body=media_body, supportsAllDrives=True
        )

        start = time.time()
        _status = None
        while not _status:
            # next_chunk() is blocking and does the actual network I/O
            _progress, _status = await run_async(insert_op.next_chunk)(num_retries=3)
            if _progress:
                now = time.time()
                chat_id = event.chat_id
                msg_id = event.id

                # Universal progress throttle logic (No_Flood)
                if len(No_Flood) > _NO_FLOOD_PRUNE_THRESHOLD:
                    for c_id in list(No_Flood.keys()):
                        for m_id in list(No_Flood[c_id].keys()):
                            if now - No_Flood[c_id][m_id] > 30:
                                del No_Flood[c_id][m_id]
                        if not No_Flood[c_id]: del No_Flood[c_id]

                if chat_id in No_Flood:
                    if msg_id in No_Flood[chat_id] and (now - No_Flood[chat_id][msg_id]) < 1.1:
                        continue
                    No_Flood[chat_id][msg_id] = now
                else:
                    No_Flood[chat_id] = {msg_id: now}

                diff = now - start
                completed = _progress.resumable_progress
                total_size = _progress.total_size
                percentage = (completed / total_size) * 100
                speed = completed / diff if diff > 0 else 0
                eta = round((total_size - completed) / speed) * 1000 if speed > 0 else 0

                filled = math.floor(percentage / 5)
                progress_str = f"`[{'●' * filled}{' ' * (20 - filled)}] {percentage:.2f}%`"

                tmp = (
                    f"{progress_str}\n\n"
                    f"`{humanbytes(completed)} of {humanbytes(total_size)}`\n\n"
                    f"`✦ Speed: {humanbytes(speed)}/s`\n\n"
                    f"`✦ ETA: {time_formatter(eta)}`"
                )
                await event.edit(f"`✦ Uploading to GDrive...`\n\n`File Name: {filename}`\n\n" + tmp)

        fileId = _status.get("id")
        try:
            await self._set_permissions(fileId=fileId)
        except BaseException:
            pass
        # execute() is blocking, run in thread
        _url = await run_async(self._build.files().get(fileId=fileId, supportsAllDrives=True).execute)()
        return _url.get("webContentLink")

    async def _download_file(self, event, fileId: str, filename: str = None):
        if fileId.startswith("http"):
            if "=download" in fileId:
                fileId = fileId.split("=")[1][:-7]
            elif "/view" in fileId:
                fileId = fileId.split("/")[::-1][1]
        try:
            if not filename:
                # get() and execute() are blocking
                info = await run_async(self._build.files().get(fileId=fileId, supportsAllDrives=True).execute)()
                filename = info["title"]

            downloader = self._build.files().get_media(
                fileId=fileId, supportsAllDrives=True
            )
        except Exception as ex:
            return False, str(ex)

        with FileIO(filename, "wb") as file:
            start = time.time()
            # 25MB chunksize for high-speed download saturation
            download = MediaIoBaseDownload(file, downloader, chunksize=25*1024*1024)
            _status = None
            while not _status:
                # next_chunk() is blocking network I/O
                _progress, _status = await run_async(download.next_chunk)(num_retries=3)
                if _progress:
                    now = time.time()
                    chat_id = event.chat_id
                    msg_id = event.id

                    # Universal progress throttle logic (No_Flood)
                    if len(No_Flood) > _NO_FLOOD_PRUNE_THRESHOLD:
                        for c_id in list(No_Flood.keys()):
                            for m_id in list(No_Flood[c_id].keys()):
                                if now - No_Flood[c_id][m_id] > 30:
                                    del No_Flood[c_id][m_id]
                            if not No_Flood[c_id]: del No_Flood[c_id]

                    if chat_id in No_Flood:
                        if msg_id in No_Flood[chat_id] and (now - No_Flood[chat_id][msg_id]) < 1.1:
                            continue
                        No_Flood[chat_id][msg_id] = now
                    else:
                        No_Flood[chat_id] = {msg_id: now}

                    diff = now - start
                    completed = _progress.resumable_progress
                    total_size = _progress.total_size
                    percentage = (completed / total_size) * 100
                    speed = completed / diff if diff > 0 else 0
                    eta = round((total_size - completed) / speed) * 1000 if speed > 0 else 0

                    filled = math.floor(percentage / 5)
                    progress_str = f"`[{'●' * filled}{' ' * (20 - filled)}] {percentage:.2f}%`"

                    tmp = (
                        f"{progress_str}\n\n"
                        f"`{humanbytes(completed)} of {humanbytes(total_size)}`\n\n"
                        f"`✦ Speed: {humanbytes(speed)}/s`\n\n"
                        f"`✦ ETA: {time_formatter(eta)}`"
                    )
                    await event.edit(f"`✦ Downloading from GDrive...`\n\n`File Name: {filename}`\n\n" + tmp)

        return True, filename

    async def _list_files(self):
        _items = await run_async(self._build.files().list(
            supportsTeamDrives=True,
            includeTeamDriveItems=True,
            spaces="drive",
            fields="nextPageToken, items(id, title, mimeType)",
            pageToken=None,
        ).execute)()
        _files = {}
        for files in _items["items"]:
            if files["mimeType"] == self.gdrive_creds["dir_mimetype"]:
                _files[self._create_folder_link(files["id"])] = files["title"]
            else:
                _files[self._create_download_link(files["id"])] = files["title"]
        return _files

    async def create_directory(self, directory):
        body = {
            "title": directory,
            "mimeType": self.gdrive_creds["dir_mimetype"],
        }
        if self.folder_id:
            body["parents"] = [{"id": self.folder_id}]

        file = await run_async(self._build.files().insert(
            body=body, supportsAllDrives=True
        ).execute)()
        fileId = file.get("id")
        await self._set_permissions(fileId=fileId)
        return fileId

    async def search(self, title):
        query = f"title contains '{title}'"
        if self.folder_id:
            query = f"'{self.folder_id}' in parents and (title contains '{title}')"

        _items = await run_async(self._build.files().list(
            supportsTeamDrives=True,
            includeTeamDriveItems=True,
            q=query,
            spaces="drive",
            fields="nextPageToken, items(id, title, mimeType)",
            pageToken=None,
        ).execute)()
        _files = {}
        for files in _items["items"]:
            _files[self._create_download_link(files["id"])] = files["title"]
        return _files
