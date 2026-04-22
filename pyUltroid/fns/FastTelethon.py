# copied from https://github.com/tulir/mautrix-telegram/blob/master/mautrix_telegram/util/parallel_file_transfer.py
# Copyright (C) 2021-2026 Tulir Asokan

import asyncio
import hashlib
import logging
import math
import os
from collections import defaultdict
from typing import (
    AsyncGenerator,
    Awaitable,
    BinaryIO,
    DefaultDict,
    List,
    Optional,
    Tuple,
    Union,
)

from telethon import TelegramClient, helpers, utils
from telethon.crypto import AuthKey
from telethon.helpers import _maybe_await
from telethon.network import MTProtoSender
from telethon.tl.alltlobjects import LAYER
from telethon.tl.functions import InvokeWithLayerRequest
from telethon.tl.functions.auth import (
    ExportAuthorizationRequest,
    ImportAuthorizationRequest,
)
from telethon.tl.functions.upload import (
    GetFileRequest,
    SaveBigFilePartRequest,
    SaveFilePartRequest,
)
from telethon.tl.types import (
    Document,
    InputDocumentFileLocation,
    InputFile,
    InputFileBig,
    InputFileLocation,
    InputPeerPhotoFileLocation,
    InputPhotoFileLocation,
    TypeInputFile,
)

log: logging.Logger = logging.getLogger("_FastTelethon")

TypeLocation = Union[
    Document,
    InputDocumentFileLocation,
    InputPeerPhotoFileLocation,
    InputFileLocation,
    InputPhotoFileLocation,
]


class DownloadSender:
    client: TelegramClient
    sender: MTProtoSender
    request: GetFileRequest
    remaining: int
    stride: int

    def __init__(
        self,
        client: TelegramClient,
        sender: MTProtoSender,
        file: TypeLocation,
        offset: int,
        limit: int,
        stride: int,
        count: int,
    ) -> None:
        self.sender = sender
        self.client = client
        self.request = GetFileRequest(file, offset=offset, limit=limit)
        self.stride = stride
        self.remaining = count

    async def next(self) -> Optional[bytes]:
        if not self.remaining:
            return None
        result = await self.client._call(self.sender, self.request)
        self.remaining -= 1
        self.request.offset += self.stride
        return result.bytes

    def disconnect(self) -> Awaitable[None]:
        return self.sender.disconnect()


class UploadSender:
    client: TelegramClient
    sender: MTProtoSender
    request: Union[SaveFilePartRequest, SaveBigFilePartRequest]
    part_count: int
    stride: int
    previous: Optional[asyncio.Task]
    loop: asyncio.AbstractEventLoop

    def __init__(
        self,
        client: TelegramClient,
        sender: MTProtoSender,
        file_id: int,
        part_count: int,
        big: bool,
        index: int,
        stride: int,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self.client = client
        self.sender = sender
        self.part_count = part_count
        if big:
            self.request = SaveBigFilePartRequest(file_id, index, part_count, b"")
        else:
            self.request = SaveFilePartRequest(file_id, index, b"")
        self.stride = stride
        self.previous = None
        self.loop = loop

    async def next(self, data: bytes) -> None:
        if self.previous:
            await self.previous
        self.previous = self.loop.create_task(self._next(data))

    async def _next(self, data: bytes) -> None:
        self.request.bytes = data
        await self.client._call(self.sender, self.request)
        self.request.file_part += self.stride
        if hasattr(self.sender, '_uploader_sent_bytes'):
            self.sender._uploader_sent_bytes += len(data)

    async def disconnect(self) -> None:
        if self.previous:
            await self.previous
        return await self.sender.disconnect()


class ParallelTransferrer:
    client: TelegramClient
    loop: asyncio.AbstractEventLoop
    dc_id: int
    senders: Optional[List[Union[DownloadSender, UploadSender]]]
    auth_key: AuthKey
    upload_ticker: int

    def __init__(self, client: TelegramClient, dc_id: Optional[int] = None) -> None:
        self.client = client
        try:
            self.client.refresh_auth(client)
        except AttributeError:
            pass
        self.loop = self.client.loop
        self.dc_id = dc_id or self.client.session.dc_id
        self.auth_key = (
            None
            if dc_id and self.client.session.dc_id != dc_id
            else self.client.session.auth_key
        )
        self.senders = None
        self.upload_ticker = 0
        self.client._uploader_sent_bytes = 0
        try:
            self.client.clear_auth(self.client)
        except AttributeError:
            pass

    async def _cleanup(self) -> None:
        await asyncio.gather(*[sender.disconnect() for sender in self.senders])
        self.senders = None

    @staticmethod
    def _get_connection_count(file_size: int) -> int:
        """Scale connection count proportionally to file size.

        Telegram allows up to 20-30 parallel upload senders per session for high-end IPs.
        Scaling too aggressively on small files wastes connection setup overhead.
        """
        if file_size <= 0:
            return 1
        mb = file_size / (1024 * 1024)
        if mb >= 100:
            return 24  # Turbo mode for large files
        if mb >= 50:
            return 16
        if mb >= 10:
            return 8
        # For small files, 4 connections is a sweet spot for VPS-to-Telegram
        return 4

    async def _init_download(
        self, connections: int, file: TypeLocation, part_count: int, part_size: int
    ) -> None:
        minimum, remainder = divmod(part_count, connections)

        def get_part_count() -> int:
            nonlocal remainder
            if remainder > 0:
                remainder -= 1
                return minimum + 1
            return minimum

        # The first cross-DC sender will export+import the authorization, so we always create it
        # before creating any other senders.
        self.senders = [
            await self._create_download_sender(
                file, 0, part_size, connections * part_size, get_part_count()
            ),
            *await asyncio.gather(
                *[
                    self._create_download_sender(
                        file, i, part_size, connections * part_size, get_part_count()
                    )
                    for i in range(1, connections)
                ]
            ),
        ]

    async def _create_download_sender(
        self,
        file: TypeLocation,
        index: int,
        part_size: int,
        stride: int,
        part_count: int,
    ) -> DownloadSender:
        return DownloadSender(
            self.client,
            await self._create_sender(),
            file,
            index * part_size,
            part_size,
            stride,
            part_count,
        )

    async def _init_upload(
        self, connections: int, file_id: int, part_count: int, big: bool
    ) -> None:
        self.senders = [
            await self._create_upload_sender(file_id, part_count, big, 0, connections),
            *await asyncio.gather(
                *[
                    self._create_upload_sender(file_id, part_count, big, i, connections)
                    for i in range(1, connections)
                ]
            ),
        ]

    async def _create_upload_sender(self, file_id: int, part_count: int, big: bool, index: int, stride: int) -> UploadSender:
        sender = await self._create_sender()
        sender._uploader_sent_bytes = 0 # Initialize local sender counter
        return UploadSender(
            self.client,
            sender,
            file_id,
            part_count,
            big,
            index,
            stride,
            loop=self.loop,
        )

    async def _create_sender(self) -> MTProtoSender:
        dc = await self.client._get_dc(self.dc_id)
        sender = MTProtoSender(self.auth_key, loggers=self.client._log)
        await sender.connect(
            self.client._connection(
                dc.ip_address,
                dc.port,
                dc.id,
                loggers=self.client._log,
                proxy=self.client._proxy,
            )
        )
        if not self.auth_key:
            auth = await self.client(ExportAuthorizationRequest(self.dc_id))
            self.client._init_request.query = ImportAuthorizationRequest(
                id=auth.id, bytes=auth.bytes
            )
            req = InvokeWithLayerRequest(LAYER, self.client._init_request)
            await sender.send(req)
            self.auth_key = sender.auth_key
        return sender

    async def init_upload(
        self,
        file_id: int,
        file_size: int,
        part_size_kb: Optional[float] = None,
        connection_count: Optional[int] = None,
    ) -> Tuple[int, int, bool]:
        connection_count = connection_count or self._get_connection_count(file_size)
        # Force 1024KB (1MB) chunks for files > 10MB to reach absolute MTProto limit
        is_large = file_size > 10 * (1024 ** 2)
        if part_size_kb is None and is_large:
            part_size_kb = 1024
        part_size = (part_size_kb or utils.get_appropriated_part_size(file_size)) * 1024
        part_count = (file_size + part_size - 1) // part_size
        await self._init_upload(connection_count, file_id, part_count, is_large)
        return int(part_size), part_count, is_large

    async def upload(self, part: bytes) -> None:
        await self.senders[self.upload_ticker].next(part)
        self.upload_ticker = (self.upload_ticker + 1) % len(self.senders)

    async def finish_upload(self) -> None:
        await self._cleanup()

    async def download(
        self,
        file: TypeLocation,
        file_size: int,
        part_size_kb: Optional[float] = None,
        connection_count: Optional[int] = None,
    ) -> AsyncGenerator[bytes, None]:
        connection_count = connection_count or self._get_connection_count(file_size)
        # Optimized for VPS: Use 1024KB (1MB) parts for large files to reduce overhead
        if part_size_kb is None and file_size > 10 * (1024 ** 2):
            part_size_kb = 512  # 512KB is safer for most DCs, can go up to 1024
        part_size = (part_size_kb or utils.get_appropriated_part_size(file_size)) * 1024
        part_count = math.ceil(file_size / part_size)
        await self._init_download(connection_count, file, part_count, part_size)

        part = 0
        while part < part_count:
            tasks = [self.loop.create_task(sender.next()) for sender in self.senders]
            for task in tasks:
                data = await task
                if not data:
                    break
                yield data
                part += 1
        await self._cleanup()


parallel_transfer_locks: DefaultDict[int, asyncio.Lock] = defaultdict(
    lambda: asyncio.Lock()
)


def stream_file(file_to_stream: BinaryIO, chunk_size=524288): # Default to 512KB for VPS throughput
    while True:
        data_read = file_to_stream.read(chunk_size)
        if not data_read:
            break
        yield data_read


async def _internal_transfer_to_telegram(
    client: TelegramClient,
    response: BinaryIO,
    filename: str,
    progress_callback: callable,
) -> Tuple[TypeInputFile, int]:
    file_id = helpers.generate_random_long()
    file_size = os.path.getsize(response.name)

    hash_md5 = hashlib.md5()
    uploader = ParallelTransferrer(client)
    part_size, part_count, is_large = await uploader.init_upload(file_id, file_size)

    # Background Progress Reporter
    async def progress_reporter():
        while uploader.senders is not None:
            if progress_callback:
                try:
                    # Sum all bytes sent across parallel senders
                    current_sent = sum(getattr(s.sender, '_uploader_sent_bytes', 0) for s in uploader.senders)
                    await _maybe_await(progress_callback(current_sent, file_size))
                except Exception:
                    pass
            await asyncio.sleep(5) # Throttled: update every 5 seconds to prioritize CPU for transfer

    reporter_task = asyncio.create_task(progress_reporter())

    buffer = bytearray()
    try:
        # Use part_size as chunk_size for perfect alignment
        for data in stream_file(response, chunk_size=part_size):
            if not is_large:
                hash_md5.update(data)
            if len(buffer) == 0 and len(data) == part_size:
                await uploader.upload(data)
                continue
            new_len = len(buffer) + len(data)
            if new_len >= part_size:
                cutoff = part_size - len(buffer)
                buffer.extend(data[:cutoff])
                await uploader.upload(bytes(buffer))
                buffer.clear()
                buffer.extend(data[cutoff:])
            else:
                buffer.extend(data)

        if len(buffer) > 0:
            await uploader.upload(bytes(buffer))

        await uploader.finish_upload()
    finally:
        reporter_task.cancel()
        # Final update
        if progress_callback:
            await _maybe_await(progress_callback(file_size, file_size))

    if is_large:
        return InputFileBig(file_id, part_count, filename), file_size
    return InputFile(file_id, part_count, filename, hash_md5.hexdigest()), file_size


async def download_file(
    client: TelegramClient,
    location: TypeLocation,
    out: BinaryIO,
    progress_callback: callable = None,
) -> BinaryIO:
    size = location.size
    dc_id, location = utils.get_input_location(location)
    # We lock the transfers because telegram has connection count limits
    downloader = ParallelTransferrer(client, dc_id)
    downloaded = downloader.download(location, size)
    async for x in downloaded:
        out.write(x)
        if progress_callback:
            try:
                await _maybe_await(progress_callback(out.tell(), size))
            except Exception:
                pass
    return out


async def upload_file(
    client: TelegramClient,
    file: BinaryIO,
    filename: str,
    progress_callback: callable = None,
) -> TypeInputFile:
    return (
        await _internal_transfer_to_telegram(client, file, filename, progress_callback)
    )[0]
