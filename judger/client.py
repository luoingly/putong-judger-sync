import asyncio
import logging
from dataclasses import asdict
from typing import Any

import aiohttp
from aiohttp import FormData

from .config import LOGGER_NAME
from .models import PreparedFile, SandboxCmd, SandboxResult

logger = logging.getLogger(f"{LOGGER_NAME}.client")


class FileCache:
    def __init__(
        self, client: "SandboxClient", expire: float = 60 * 60, recycle_gap: float = 60
    ) -> None:
        self.client = client
        self.expire = expire
        self.recycle_gap = recycle_gap
        self.files: dict[str, PreparedFile] = {}
        self.last_access: dict[str, float] = {}
        self.recycle_task: asyncio.Task[None] | None = None
        self.cleanup_tasks: list[asyncio.Task[None]] = []
        self._lock = asyncio.Lock()
        self._closed = False

        logger.debug("File cache initialized with expire=%s, recycle_gap=%s", expire, recycle_gap)

    async def __aenter__(self) -> "FileCache":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def close(self) -> None:
        if self._closed:
            return

        self._closed = True
        if self.recycle_task:
            self.recycle_task.cancel()
            try:
                await self.recycle_task
            except asyncio.CancelledError:
                pass

        async with self._lock:
            for identifier, file in self.files.items():
                logger.debug("Cleaning up file '%s' on close", identifier)
                self.cleanup_tasks.append(asyncio.create_task(self.client.delete_file(file.fileId)))
            if self.cleanup_tasks:
                await asyncio.gather(*self.cleanup_tasks)

            self.files.clear()
            self.last_access.clear()

        logger.debug("File cache closed")

    def time(self) -> float:
        return asyncio.get_event_loop().time()

    async def _recycle(self) -> None:
        async with self._lock:
            current_time = self.time()
            to_delete = [
                (identifier, self.files[identifier].fileId)
                for identifier, last_access in self.last_access.items()
                if current_time - last_access > self.expire
            ]

            for identifier, file_id in to_delete:
                logger.debug("Recycling expired file '%s'", identifier)
                self.cleanup_tasks.append(asyncio.create_task(self.client.delete_file(file_id)))
                self.files.pop(identifier, None)
                self.last_access.pop(identifier, None)

            for task in self.cleanup_tasks:
                if task.done():
                    self.cleanup_tasks.remove(task)

    async def recycle(self) -> None:
        try:
            while not self._closed:
                await self._recycle()
                await asyncio.sleep(self.recycle_gap)
        except asyncio.CancelledError:
            logger.debug("Recycle task cancelled")
            raise

    async def get(self, identifier: str) -> PreparedFile | None:
        async with self._lock:
            file = self.files.get(identifier)

            if file is not None:
                self.last_access[identifier] = self.time()
                logger.debug("Accessed file '%s'", identifier)
            else:
                logger.debug("File '%s' not found in cache", identifier)
            return file

    async def set(self, identifier: str, file: PreparedFile) -> None:
        async with self._lock:
            if identifier in self.files:
                logger.debug("Updating existing file '%s' in cache", identifier)
                self.cleanup_tasks.append(
                    asyncio.create_task(self.client.delete_file(self.files[identifier].fileId))
                )
            else:
                logger.debug("Adding new file '%s' to cache", identifier)

            self.files[identifier] = file
            self.last_access[identifier] = self.time()

        if self.recycle_task is None and not self._closed:
            self.recycle_task = asyncio.create_task(self.recycle())
            logger.debug("Started recycle task")


class SandboxClient:
    def __init__(self, endpoint: str) -> None:
        self.endpoint = endpoint.strip("/")
        self.session = aiohttp.ClientSession()
        self.cache = FileCache(client=self)
        logger.debug("Sandbox client initialized with: %s", self.endpoint)

    def __repr__(self) -> str:
        return f"SandboxClient(endpoint='{self.endpoint}')"

    async def __aenter__(self) -> "SandboxClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def close(self) -> None:
        await self.cache.close()
        await self.session.close()
        logger.debug("Sandbox client closed")

    async def run_command(
        self, commands: list[SandboxCmd], pipeMapping: list[dict] | None = None
    ) -> list[SandboxResult]:
        url = f"{self.endpoint}/run"
        payload = {"cmd": [asdict(c) for c in commands]}
        if pipeMapping:
            payload["pipeMapping"] = pipeMapping
        logger.debug("Sending run command: %s", payload)

        async with self.session.post(url, json=payload) as resp:
            resp.raise_for_status()
            results = await resp.json()
            logger.debug("Received run results: %s", results)
            return [SandboxResult(**result) for result in results]

    async def upload_file(self, content: str, filename: str = "file.txt") -> PreparedFile:
        url = f"{self.endpoint}/file"
        data = FormData()
        data.add_field("file", content, filename=filename)
        logger.debug("Uploading file with %d bytes", len(content))

        async with self.session.post(url, data=data) as resp:
            resp.raise_for_status()
            result = await resp.json()
            logger.debug("Received upload results: '%s'", result)
            return PreparedFile(result)

    async def download_file(self, file_id: str) -> str | None:
        url = f"{self.endpoint}/file/{file_id}"
        logger.debug("Downloading file: '%s'", file_id)

        async with self.session.get(url) as resp:
            result = await resp.text()
            if resp.status == 200:
                logger.debug("Received file '%s' with %d bytes", file_id, len(result))
                return result
            else:
                logger.warning(
                    "Failed to download file '%s': %d %s", file_id, resp.status, await resp.text()
                )
                return None

    async def delete_file(self, file_id: str) -> bool:
        url = f"{self.endpoint}/file/{file_id}"
        logger.debug("Deleting file '%s'", file_id)

        async with self.session.delete(url) as resp:
            if resp.status == 200:
                logger.debug("File '%s' deleted", file_id)
                return True
            else:
                logger.warning(
                    "Failed to delete file '%s': %d %s", file_id, resp.status, await resp.text()
                )
                return False

    async def get_version(self) -> dict[str, Any]:
        url = f"{self.endpoint}/version"
        logger.debug("Getting version")

        async with self.session.get(url) as resp:
            result = await resp.json()
            logger.debug("Received version: %s", result)
            return result
