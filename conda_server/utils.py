import functools
import os
from pathlib import Path


@functools.lru_cache(maxsize=1)
def get_platforms() -> set[str]:
    return {
        "linux-32",
        "linux-64",
        "linux-aarch64",
        "linux-armv6l",
        "linux-armv7l",
        "linux-ppc64",
        "linux-ppc64le",
        "linux-s390x",
        "noarch",
        "osx-64",
        "osx-arm64",
        "win-32",
        "win-64",
        "win-arm64",
        "zos-z",
    }


@functools.lru_cache(maxsize=1)
def get_channel_dir() -> str:
    return os.getenv(
        "CONDA_CHANNEL_DIR", str(Path.home() / ".conda-server" / "channel")
    )
