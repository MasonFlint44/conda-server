import asyncio
import logging
import re

from conda_index.cli import cli
from fastapi.concurrency import run_in_threadpool
from filelock import FileLock
from watchfiles import Change, DefaultFilter, awatch

from .atomic import safely_remove_lock_file
from .utils import get_channel_dir

logger = logging.getLogger(__name__)


# See https://github.com/conda/conda-index
class IndexManager:
    def __init__(self) -> None:
        self._pending_index_generation_lock = FileLock(
            f"{get_channel_dir()}/.pending_index_generation.lock"
        )
        self._index_generation_lock = FileLock(
            f"{get_channel_dir()}/.index_generation.lock"
        )
        self._watch_task: asyncio.Task[None] | None = None
        self._stop_watching_event = asyncio.Event()

    @property
    def is_watching(self) -> bool:
        return self._watch_task is not None

    async def generate_index(
        self, file_changes: set[tuple[Change, str]] | None = None
    ) -> None:
        # Only allow one executing generation and one follow-up pending generation to
        # be executing at the same time.
        if self._pending_index_generation_lock.is_locked:
            logger.info(
                "Canceling index generation. There is already a pending index generation."
            )
            return

        try:
            if self._index_generation_lock.is_locked:
                logger.info(
                    "An index generation is already in progress. Scheduling a pending index generation."
                )
                self._pending_index_generation_lock.acquire()

            try:
                with self._index_generation_lock:
                    logger.info("Generating index.")
                    await run_in_threadpool(
                        cli.callback,  # type: ignore
                        get_channel_dir(),  # type: ignore
                        channeldata=True,
                        bz2=True,
                        zst=True,
                        rss=True,
                    )
            finally:
                safely_remove_lock_file(f"{get_channel_dir()}/.index_generation.lock")

            if self._pending_index_generation_lock.is_locked:
                self._pending_index_generation_lock.release()
        finally:
            if self._pending_index_generation_lock.is_locked:
                safely_remove_lock_file(
                    f"{get_channel_dir()}/.pending_index_generation.lock"
                )

    def watch_channel_dir(self) -> None:
        if self.is_watching:
            logger.info("Already watching the channel directory.")
            return
        # Start watching the channel directory for changes
        logger.info("Watching the channel directory for changes.")
        self._watch_task = asyncio.create_task(self._watch_channel_dir())
        self._watch_task.add_done_callback(self._on_watch_done)

    def stop_watching(self) -> None:
        if not self.is_watching:
            return
        self._stop_watching_event.set()
        logger.info("Stopped watching the channel directory.")
        self._stop_watching_event.clear()

    async def _watch_channel_dir(self) -> None:
        # Watch the channel directory for changes
        async for change in awatch(
            get_channel_dir(),
            stop_event=self._stop_watching_event,
            watch_filter=IndexFilter(),
        ):
            # Generate the index when a change is detected
            await self.generate_index(change)

    def _on_watch_done(self, task: asyncio.Task[None]) -> None:
        self._watch_task = None

    def __enter__(self) -> "IndexManager":
        self.watch_channel_dir()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.stop_watching()


class IndexFilter(DefaultFilter):
    generated_files = {
        ".index_generation.lock",
        ".pending_index_generation.lock",
        "current_repodata.json",
        "current_repodata.json.bz2",
        "current_repodata.json.zst",
        "repodata.json",
        "repodata.json.bz2",
        "repodata.json.zst",
        "repodata_from_packages.json",
        "repodata_from_packages.json.bz2",
        "repodata_from_packages.json.zst",
        "patch_instructions.json",  # TODO: does --patch-generator create this file?
        "patch_instructions.json.bz2",
        "patch_instructions.json.zst",
        "channeldata.json",
        "index.html",
        "rss.xml",
        "run_exports.json",
        "current_index.json",  # TODO: does --current-index-versions-file create this file?
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
