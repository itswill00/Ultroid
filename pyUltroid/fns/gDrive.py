# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/TeamUltroid/pyUltroid/blob/main/LICENSE>.

import json
import math
import os
import time
from io import FileIO
from logging import WARNING, getLogger

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

from .. import udB
from .helper import (
    _NO_FLOOD_PRUNE_THRESHOLD,
    No_Flood,
    humanbytes,
    run_async,
    time_formatter,
)

LOGS = getLogger(__name__)

# Mute noisy google logs
for log_name in ["googleapiclient.discovery_cache", "googleapiclient.discovery", "google_auth_oauthlib.flow"]:
    getLogger(log_name).setLevel(WARNING)


class GDriveManager:
    def __init__(self):
        self._flow = None
        self.scopes = [
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive.metadata",
        ]
        self.dir_mimetype = "application/vnd.google-apps.folder"
        self.folder_id = udB.get_key("GDRIVE_FOLDER_ID")
        self.token_file = "resources/auth/gdrive_creds.json"
        self._creds = None
        self._service = None

    @staticmethod
    def _create_download_link(fileId: str):
        return f"https://drive.google.com/uc?id={fileId}&export=download"

    @staticmethod
    def _create_folder_link(folderId: str):
        return f"https://drive.google.com/folderview?id={folderId}"

    def _get_client_config(self):
        c_id = udB.get_key("GDRIVE_CLIENT_ID")
        c_secret = udB.get_key("GDRIVE_CLIENT_SECRET")
        if c_id and c_secret:
            client_id = str(c_id).strip().strip('"').strip("'")
            client_secret = str(c_secret).strip().strip('"').strip("'")
        else:
            client_id = "458306970678-jhfbv6o5sf1ar63o1ohp4c0grblp8qba.apps.googleusercontent.com"
            client_secret = "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"

        return {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "redirect_uris": ["http://localhost"]
            }
        }

    def _create_token_file(self, code: str = None):
        client_config = self._get_client_config()
        # Note: We use a redirect_uri that allows OOB-like behavior (copy-paste)
        # Even though OOB is deprecated, 'http://localhost' still works for Desktop apps
        # to generate a code if the user is technical enough to copy from address bar,
        # OR we can use a special redirect URI if available.
        # For compatibility with Ultroid's current flow, we'll try to get it working.
        
        if code:
            if not self._flow:
                self._flow = Flow.from_client_config(
                    client_config,
                    scopes=self.scopes,
                    redirect_uri="http://localhost"
                )
            try:
                self._flow.fetch_token(code=code)
                creds = self._flow.credentials
                with open(self.token_file, "w") as f:
                    f.write(creds.to_json())
                udB.set_key("GDRIVE_AUTH_TOKEN", creds.to_json())
                self._creds = creds
                return True
            except Exception as e:
                LOGS.error(f"GDrive Auth Error: {e}")
                return False

        self._flow = Flow.from_client_config(
            client_config,
            scopes=self.scopes,
            redirect_uri="http://localhost" # Standard for Desktop apps after OOB deprecation
        )
        auth_url, _ = self._flow.authorization_url(prompt="consent")
        return auth_url

    def _load_creds(self):
        if self._creds:
            return self._creds
        
        token_data = udB.get_key("GDRIVE_AUTH_TOKEN")
        if token_data:
            try:
                self._creds = Credentials.from_authorized_user_info(json.loads(token_data), self.scopes)
            except Exception:
                if os.path.exists(self.token_file):
                    self._creds = Credentials.from_authorized_user_file(self.token_file, self.scopes)
        
        if self._creds and self._creds.expired and self._creds.refresh_token:
            try:
                self._creds.refresh(Request())
                with open(self.token_file, "w") as f:
                    f.write(self._creds.to_json())
                udB.set_key("GDRIVE_AUTH_TOKEN", self._creds.to_json())
            except Exception as e:
                LOGS.error(f"Failed to refresh GDrive token: {e}")
                self._creds = None
        
        return self._creds

    @property
    def service(self):
        if self._service:
            return self._service
        creds = self._load_creds()
        if not creds:
            return None
        self._service = build("drive", "v3", credentials=creds, cache_discovery=False)
        return self._service

    async def _set_permissions(self, fileId: str):
        if not self.service: return
        _permissions = {
            "role": "reader",
            "type": "anyone",
        }
        await run_async(self.service.permissions().create(
            fileId=fileId, body=_permissions, supportsAllDrives=True
        ).execute)()

    async def _upload_file(self, event, path: str, filename: str = None, folder_id: str = None):
        if not self.service: return "Please Authorise GDrive first."
        
        if not filename:
            filename = os.path.basename(path)
        
        from mimetypes import guess_type
        mime_type = guess_type(path)[0] or "application/octet-stream"

        # Optimized chunksize for faster transfer on stable connections
        media_body = MediaFileUpload(path, mimetype=mime_type, resumable=True, chunksize=10*1024*1024)
        body = {
            "name": filename,
            "description": "Uploaded using Ultroid Userbot",
            "mimeType": mime_type,
        }
        
        target_folder = folder_id or self.folder_id
        if target_folder:
            body["parents"] = [target_folder]

        insert_op = self.service.files().create(
            body=body, media_body=media_body, supportsAllDrives=True
        )

        start = time.time()
        _status = None
        last_edit_time = 0
        
        while not _status:
            _progress, _status = await run_async(insert_op.next_chunk)(num_retries=5)
            if _progress:
                now = time.time()
                # Throttle edits to max ~1 per 1.5 seconds to avoid Telegram flood
                if now - last_edit_time < 1.5:
                    continue
                last_edit_time = now

                completed = _progress.resumable_progress
                total_size = _progress.total_size
                percentage = (completed / total_size) * 100
                speed = completed / (now - start) if (now - start) > 0 else 0
                eta = round((total_size - completed) / speed) if speed > 0 else 0

                filled = math.floor(percentage / 5)
                progress_str = f"`[{'●' * filled}{' ' * (20 - filled)}] {percentage:.2f}%`"
                
                tmp = (
                    f"**✦ Uploading to GDrive...**\n"
                    f"**File:** `{filename}`\n\n"
                    f"{progress_str}\n"
                    f"`{humanbytes(completed)} / {humanbytes(total_size)}`\n"
                    f"**Speed:** `{humanbytes(speed)}/s`\n"
                    f"**ETA:** `{time_formatter(eta*1000)}`"
                )
                try:
                    await event.edit(tmp)
                except Exception: pass

        fileId = _status.get("id")
        try:
            await self._set_permissions(fileId=fileId)
        except Exception: pass
        
        return self._create_download_link(fileId)

    async def _download_file(self, event, fileId: str, filename: str = None):
        if not self.service: return False, "Please Authorise GDrive first."
        
        if fileId.startswith("http"):
            if "id=" in fileId:
                fileId = fileId.split("id=")[1].split("&")[0]
            elif "/file/d/" in fileId:
                fileId = fileId.split("/file/d/")[1].split("/")[0]
            elif "/folders/" in fileId:
                 fileId = fileId.split("/folders/")[1].split("/")[0]

        try:
            if not filename:
                info = await run_async(self.service.files().get(fileId=fileId, supportsAllDrives=True).execute)()
                filename = info["name"]

            request = self.service.files().get_media(fileId=fileId, supportsAllDrives=True)
        except Exception as ex:
            return False, str(ex)

        with FileIO(filename, "wb") as file:
            start = time.time()
            downloader = MediaIoBaseDownload(file, request, chunksize=10*1024*1024)
            _status = None
            last_edit_time = 0
            
            while not _status:
                _progress, _status = await run_async(downloader.next_chunk)(num_retries=5)
                if _progress:
                    now = time.time()
                    if now - last_edit_time < 1.5:
                        continue
                    last_edit_time = now

                    completed = _progress.resumable_progress
                    total_size = _progress.total_size
                    percentage = (completed / total_size) * 100
                    speed = completed / (now - start) if (now - start) > 0 else 0
                    eta = round((total_size - completed) / speed) if speed > 0 else 0

                    filled = math.floor(percentage / 5)
                    progress_str = f"`[{'●' * filled}{' ' * (20 - filled)}] {percentage:.2f}%`"

                    tmp = (
                        f"**✦ Downloading from GDrive...**\n"
                        f"**File:** `{filename}`\n\n"
                        f"{progress_str}\n"
                        f"`{humanbytes(completed)} / {humanbytes(total_size)}`\n"
                        f"**Speed:** `{humanbytes(speed)}/s`\n"
                        f"**ETA:** `{time_formatter(eta*1000)}`"
                    )
                    try:
                        await event.edit(tmp)
                    except Exception: pass

        return True, filename

    async def _list_files(self):
        if not self.service: return {}
        try:
            _items = await run_async(self.service.files().list(
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                spaces="drive",
                fields="nextPageToken, files(id, name, mimeType)",
                pageSize=100,
            ).execute)()
            
            _files = {}
            for file in _items.get("files", []):
                if file["mimeType"] == self.dir_mimetype:
                    _files[self._create_folder_link(file["id"])] = file["name"]
                else:
                    _files[self._create_download_link(file["id"])] = file["name"]
            return _files
        except Exception as e:
            LOGS.error(f"GDrive List Error: {e}")
            return {}

    async def create_directory(self, directory):
        if not self.service: return None
        body = {
            "name": directory,
            "mimeType": self.dir_mimetype,
        }
        if self.folder_id:
            body["parents"] = [self.folder_id]

        file = await run_async(self.service.files().create(
            body=body, supportsAllDrives=True
        ).execute)()
        fileId = file.get("id")
        await self._set_permissions(fileId=fileId)
        return fileId

    async def search(self, title):
        if not self.service: return {}
        query = f"name contains '{title}'"
        if self.folder_id:
            query = f"'{self.folder_id}' in parents and (name contains '{title}')"

        try:
            _items = await run_async(self.service.files().list(
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                q=query,
                spaces="drive",
                fields="nextPageToken, files(id, name, mimeType)",
            ).execute)()
            
            _files = {}
            for file in _items.get("files", []):
                _files[self._create_download_link(file["id"])] = file["name"]
            return _files
        except Exception as e:
            LOGS.error(f"GDrive Search Error: {e}")
            return {}
