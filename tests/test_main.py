from pathlib import Path
from os.path import basename
from httpx import AsyncClient
import glob
import shutil


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
        == "4b8561fe7c20ff2cc8f58c4efbc1cb1102e4fe559fbafbe1bc564ec33134d3da"
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
    assert response.json()["md5"] == "09cd4ce1cd95df5982ac45e8ac4ae5f5"


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
