import glob
import os
import time
from contextlib import suppress
from datetime import datetime, timedelta
from pathlib import Path

from conda_server.index import IndexManager
from conda_server.utils import get_platforms


async def test_generate_index(channel_dir: Path):
    # Delete the index files if they exist
    for platform in get_platforms():
        if Path(channel_dir, platform).exists():
            with suppress(FileNotFoundError):
                Path(channel_dir, platform, "repodata_from_packages.json").unlink()
                Path(channel_dir, platform, "repodata.json").unlink()
                Path(channel_dir, platform, "current_repodata.json").unlink()
                Path(channel_dir, platform, "index.html").unlink()
                cache_dbs = glob.glob(
                    f"{platform}/.cache/**", root_dir=channel_dir, recursive=True
                )
                for cache_db in cache_dbs:
                    if cache_db == f"{platform}/.cache/":
                        continue
                    Path(channel_dir, cache_db).unlink()
                Path(channel_dir, platform, ".cache").rmdir()

    index_manager = IndexManager()

    current_time = datetime.now()
    index_start_time = time.perf_counter()
    await index_manager.generate_index()
    index_end_time = time.perf_counter()

    assert Path(channel_dir, ".pending_index_generation.lock").exists() is False
    assert Path(channel_dir, ".index_generation.lock").exists() is False

    def file_modified_within_delta(
        path: Path, time_: datetime, delta: timedelta
    ) -> bool:
        file_modified_time = datetime.fromtimestamp(os.path.getmtime(path))
        return time_ <= file_modified_time < time_ + delta

    def files_modified_within_delta(
        dir_path: Path, filenames: list[str], time_: datetime, delta: timedelta
    ) -> bool:
        return all(
            file_modified_within_delta(dir_path.joinpath(filename), time_, delta)
            for filename in filenames
        )

    assert files_modified_within_delta(
        Path(channel_dir, "noarch"),
        [
            "repodata_from_packages.json",
            "repodata.json",
            "current_repodata.json",
            "index.html",
            ".cache/cache.db",
        ],
        current_time,
        timedelta(seconds=index_end_time - index_start_time),
    )

    for platform in get_platforms():
        if platform == "noarch":
            continue
        if not Path(channel_dir, platform).exists():
            continue

        assert files_modified_within_delta(
            Path(channel_dir, platform),
            [
                "repodata_from_packages.json",
                "repodata.json",
                "current_repodata.json",
                "index.html",
                ".cache/cache.db",
            ],
            current_time,
            timedelta(seconds=index_end_time - index_start_time),
        )
