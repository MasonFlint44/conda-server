import asyncio
import glob
import shutil
from os.path import basename
from pathlib import Path
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from watchfiles import Change


async def test_upload(testpkg: Path, async_client: AsyncClient, channel_dir: Path):
    # Delete the package from the server if it exists
    Path.unlink(channel_dir / "linux-64" / basename(testpkg), missing_ok=True)

    # Ensure the package file does not exist on the server
    assert not glob.glob(
        f"linux-64/{basename(testpkg)}", root_dir=channel_dir, recursive=True
    )

    # Upload the package to the server
    with open(testpkg, "rb") as f:
        response = await async_client.put(
            f"/linux-64/{basename(testpkg)}", files={"file": f}
        )
    assert response.status_code == 200

    # Ensure the package file exists on the server
    assert glob.glob(
        f"linux-64/{basename(testpkg)}", root_dir=channel_dir, recursive=True
    )


@patch("conda_server.index.IndexManager.generate_index")
async def test_upload_triggers_indexing(
    mocked_generate_index: AsyncMock,
    testpkg: Path,
    async_client: AsyncClient,
    channel_dir: Path,
):
    # Upload the package to the server
    with open(testpkg, "rb") as f:
        response = await async_client.put(
            f"/linux-64/{basename(testpkg)}", files={"file": f}
        )
    assert response.status_code == 200

    # wait for indexing to run
    await asyncio.sleep(0.1)

    assert mocked_generate_index.await_args
    temp_file_name = basename(
        [
            await_args
            for await_args in mocked_generate_index.await_args[0][0]
            if await_args[1].endswith(".tmp")
        ][0][1]
    )

    assert Change.added, (
        channel_dir.joinpath(f"/linux-64/{basename(testpkg)}.lock")
        in mocked_generate_index.await_args[0][0]
    )
    assert Change.added, channel_dir.joinpath(f"/linux-64/{temp_file_name}")
    assert Change.deleted, channel_dir.joinpath(f"/linux-64/{temp_file_name}")
    assert Change.added, (
        channel_dir.joinpath(f"/linux-64/{basename(testpkg)}")
        in mocked_generate_index.await_args[0][0]
    )
    assert Change.deleted, (
        channel_dir.joinpath(f"/linux-64/{basename(testpkg)}.lock")
        in mocked_generate_index.await_args[0][0]
    )


async def test_delete(testpkg: Path, async_client: AsyncClient, channel_dir: Path):
    # Copy the package to the server
    shutil.copy(testpkg, channel_dir / "linux-64" / basename(testpkg))

    # Ensure the package file exists on the server
    assert glob.glob(
        f"linux-64/{basename(testpkg)}", root_dir=channel_dir, recursive=True
    )

    # Delete the package from the server
    response = await async_client.delete(f"/linux-64/{basename(testpkg)}")
    assert response.status_code == 200

    # Ensure the package file does not exist on the server
    assert not glob.glob(
        f"linux-64/{basename(testpkg)}", root_dir=channel_dir, recursive=True
    )


async def test_hash_sha256(testpkg: Path, async_client: AsyncClient, channel_dir: Path):
    # Copy the package to the server
    shutil.copy(testpkg, channel_dir / "linux-64" / basename(testpkg))

    # Ensure the package file exists on the server
    assert glob.glob(
        f"linux-64/{basename(testpkg)}", root_dir=channel_dir, recursive=True
    )

    # Get the sha256 hash of the package
    response = await async_client.get(f"/linux-64/{basename(testpkg)}/hash/sha256")
    assert response.status_code == 200
    assert (
        response.json()["sha256"]
        == "f74353fc376dd8732662cde39e0103080cb7e03c6df4e13a6efa21cd484c48f6"
    )


async def test_hash_md5(testpkg: Path, async_client: AsyncClient, channel_dir: Path):
    # Copy the package to the server
    shutil.copy(testpkg, channel_dir / "linux-64" / basename(testpkg))

    # Ensure the package file exists on the server
    assert glob.glob(
        f"linux-64/{basename(testpkg)}", root_dir=channel_dir, recursive=True
    )

    # Get the md5 hash of the package
    response = await async_client.get(f"/linux-64/{basename(testpkg)}/hash/md5")
    assert response.status_code == 200
    assert response.json()["md5"] == "ec370971727ce7870eba47f8ad2847ba"


async def test_get_package(testpkg: Path, async_client: AsyncClient, channel_dir: Path):
    # Copy the package to the server
    shutil.copy(testpkg, channel_dir / "linux-64" / basename(testpkg))

    # Ensure the package file exists on the server
    assert glob.glob(
        f"linux-64/{basename(testpkg)}", root_dir=channel_dir, recursive=True
    )

    # Get the package
    response = await async_client.get(f"/linux-64/{basename(testpkg)}")
    assert response.status_code == 200
    assert response.content == testpkg.read_bytes()
    assert (
        response.headers["Content-Disposition"]
        == f'attachment; filename="{basename(testpkg)}"'
    )
    assert response.headers["Content-Type"] == "application/x-tar"
    assert response.headers["Content-Length"] == str(testpkg.stat().st_size)
