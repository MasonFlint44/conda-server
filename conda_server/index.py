import asyncio
import re

from conda_index.cli import cli
from fastapi.concurrency import run_in_threadpool
from watchfiles import Change, DefaultFilter, awatch

from .utils import get_channel_dir


# See https://github.com/conda/conda-index
class IndexManager:
    def __init__(self) -> None:
        self._index_generation_semaphore = asyncio.BoundedSemaphore(2)
        self._index_generation_lock = asyncio.Lock()
        self._watch_task: asyncio.Task[None] | None = None
        self._stop_watching_event = asyncio.Event()

    @property
    def is_watching(self) -> bool:
        return self._watch_task is not None

    async def generate_index(self) -> None:
        # Only allow two index generations to be pending at the same time:
        # one executing generation and one followup generation waiting to be executed.
        #
        # The lock ensure only one index generation is executing at a time.
        if self._index_generation_semaphore.locked():
            return

        async with self._index_generation_semaphore, self._index_generation_lock:
            await run_in_threadpool(cli.callback, get_channel_dir())  # type: ignore

    def watch_channel_dir(self) -> None:
        if self.is_watching:
            return
        # Start watching the channel directory for changes
        self._watch_task = asyncio.create_task(self._watch_channel_dir())
        self._watch_task.add_done_callback(self._on_watch_done)

    def stop_watching(self) -> None:
        if not self.is_watching:
            return
        self._stop_watching_event.set()
        self._stop_watching_event.clear()

    async def _watch_channel_dir(self) -> None:
        # Watch the channel directory for changes
        async for _ in awatch(
            get_channel_dir(),
            stop_event=self._stop_watching_event,
            watch_filter=IndexFilter(),
        ):
            # Generate the index when a change is detected
            await self.generate_index()

    def _on_watch_done(self, task: asyncio.Task[None]) -> None:
        self._watch_task = None


class IndexFilter(DefaultFilter):
    generated_files = {
        "repodata.json",
        "repodata.json.bz2",
        "repodata.json.zst",
        "repodata_from_packages.json",
        "index.html",
        "current_repodata.json",
        "rss.xml",
        "run_exports.json",
        "current_index.json",  # TODO: does --current-index-versions-file create this file?
        "channeldata.json",
        "patch_instructions.json",  # TODO: does --patch-generator create this file?
    }
    uuid_pattern = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    pattern = re.compile(rf".*\/({'|'.join(generated_files)})(\.{uuid_pattern})?")
    cache_dir = ".cache"

    def __call__(self, change: Change, path: str) -> bool:
        return (
            super().__call__(change, path)
            and not bool(self.pattern.match(path))
            and self.cache_dir not in path
        )
