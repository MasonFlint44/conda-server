import asyncio
from fastapi.concurrency import run_in_threadpool

from conda_index.cli import cli

from .utils import get_channel_dir


# See https://github.com/conda/conda-index
class IndexManager:
    def __init__(self) -> None:
        self._index_generation_semaphore = asyncio.BoundedSemaphore(2)
        self._index_generation_lock = asyncio.Lock()

    async def generate_index(self) -> None:
        # Only allow two index generations to be pending at the same time:
        # one executing generation and one followup generation waiting to be executed.
        # 
        # The lock ensure only one index generation is executing at a time.
        if self._index_generation_semaphore.locked():
            return

        async with self._index_generation_semaphore, self._index_generation_lock:
            await run_in_threadpool(cli.callback, get_channel_dir()) # type: ignore
