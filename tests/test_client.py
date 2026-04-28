import asyncio
import os
import pytest
from judger.models import PreparedFile
from judger.client import SandboxClient, FileCache

endpoint = os.getenv('PTOJ_SANDBOX_ENDPOINT', 'http://localhost:5050')

file_content = \
    "In the intricate dance of algorithms and the language of programming, " + \
    "the undefined variable is a transient anomaly waiting to be tamed. As " + \
    "programmers navigate the complexities of their craft, the quest for a " + \
    "well-defined codebase becomes a journey of discovery, where each " + \
    "undefined variable is a stepping stone toward mastery in the " + \
    "ever-evolving world of software development."


@pytest.mark.asyncio
async def test_client_repr():
    async with SandboxClient(endpoint) as client:
        assert endpoint in repr(client)


@pytest.mark.asyncio
async def test_client_get_version():
    async with SandboxClient(endpoint) as client:
        version = await client.get_version()
        assert isinstance(version, dict)
        assert 'buildVersion' in version


@pytest.mark.asyncio
async def test_client_file_manage():
    async with SandboxClient(endpoint) as client:

        file = await client.upload_file(file_content)
        assert isinstance(file, PreparedFile)

        file_id = file.fileId
        assert isinstance(file_id, str)

        downloaded = await client.download_file(file_id)
        assert isinstance(downloaded, str)
        assert downloaded == file_content

        assert await client.delete_file(file_id)


@pytest.mark.asyncio
async def test_client_download_nonexistent_file():
    async with SandboxClient(endpoint) as client:
        assert await client.download_file("nonexistent") is None


@pytest.mark.asyncio
async def test_client_delete_nonexistent_file():
    async with SandboxClient(endpoint) as client:
        assert not await client.delete_file("nonexistent")


@pytest.mark.asyncio
async def test_file_cache_basic():
    async with SandboxClient(endpoint) as client:
        test_file_1 = await client.upload_file(file_content)
        await client.cache.set("test", test_file_1)
        assert await client.cache.get("test") == test_file_1
        test_file_2 = await client.upload_file(file_content)
        await client.cache.set("test", test_file_2)
        assert await client.cache.get("test") == test_file_2


@pytest.mark.asyncio
async def test_file_cache_recycle():
    async with SandboxClient(endpoint) as client:
        async with FileCache(client, expire=0.1, recycle_gap=0.05) as cache:
            test_file = await client.upload_file(file_content)
            await cache.set("test2", test_file)
            await asyncio.sleep(0.2)
            assert await cache.get("test2") is None


@pytest.mark.asyncio
async def test_file_cache_thread_safety():
    async with SandboxClient(endpoint) as client:
        async def worker(key: str):
            file = await client.upload_file(key)
            await client.cache.set(key, file)
            assert await client.cache.get(key) == file
        tasks = [asyncio.create_task(worker(f"key{i}")) for i in range(10)]
        await asyncio.gather(*tasks)


@pytest.mark.asyncio
async def test_file_cache_close():
    async with SandboxClient(endpoint) as client:
        await client.cache.close()
