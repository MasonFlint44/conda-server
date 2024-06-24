import asyncio
import os
import shutil
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, File, HTTPException, Path, Security, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from fastapi.security.api_key import APIKeyHeader
from prometheus_fastapi_instrumentator import Instrumentator

from .atomic import atomic_write
from .hash import md5_in_chunks, sha256_in_chunks
from .index import IndexManager
from .utils import (
    get_channel_dir,
    get_package_file_name,
    get_package_file_path,
    get_platforms,
)
from .validation import PLATFORM_REGEX, validate_package_name

# TODO: add custom metrics for package downloads
# TODO: support rss feed
# TODO: validate uploaded file is a valid conda package - at least validate platform
# TODO: implement authentication - should be configurable for both download and upload
# TODO: add logging

# TODO: implement rate limiting - should be configurable
# TODO: add configurable file size limit
# TODO: implement search endpoints
# TODO: abstract away the file system to make it easier to implement other backing stores - look into fuse and alternatives
# TODO: implement s3 backing store
# TODO: implement sqlite backing store
# TODO: implement postgres backing store

API_KEY = os.getenv("CONDA_SERVER_API_KEY", "default")
API_KEY_NAME = "X-API-Key"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Validate channel directory is not a supported platform
    assert (
        os.path.basename(get_channel_dir()) not in get_platforms()
    ), "$CONDA_CHANNEL_DIR cannot be a supported platform."

    # Create the channel and noarch directories if they don't exist
    os.makedirs(os.path.join(get_channel_dir(), "noarch"), exist_ok=True)

    # Expose prometheus metrics endpoint
    instrumentator.expose(app)

    # Start watching the channel directory for changes
    with index_manager:
        yield


app = FastAPI(
    lifespan=lifespan,  # type: ignore
)
loop = asyncio.get_event_loop()
index_manager = IndexManager()
instrumentator = Instrumentator().instrument(app)


def get_api_key(
    api_key_header: str = Security(APIKeyHeader(name=API_KEY_NAME)),
):
    if api_key_header == API_KEY:
        return api_key_header
    raise HTTPException(status_code=400, detail="API Key was not provided")


@app.post("/build-index")
async def build_index(
    # api_key: APIKeyHeader = Depends(get_api_key),
):
    await index_manager.generate_index()
    return {"message": "Index built successfully"}


@app.get("/{platform}/{package_file}")
async def fetch_package(
    package_file: str,
    platform: str = Path(pattern=PLATFORM_REGEX),
):
    # Validate the package file name
    package_name, package_version, package_build, file_extension = (
        validate_package_name(package_file)
    )

    file_name = get_package_file_name(
        package_name, package_version, package_build, file_extension
    )
    file_path = get_package_file_path(get_channel_dir(), platform, file_name)
    media_type = (
        "application/x-tar"
        if file_extension == "tar.bz2"
        else "application/octet-stream"
    )

    try:
        # Return the file as a response
        return FileResponse(path=file_path, media_type=media_type, filename=file_name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="File not found") from e


@app.put("/{platform}/{package_file}")
async def upload_package(
    package_file: str,
    platform: str = Path(pattern=PLATFORM_REGEX),
    file: UploadFile = File(...),
    # api_key: APIKeyHeader = Depends(get_api_key),
):
    # Validate the package file name
    package_name, package_version, package_build, file_extension = (
        validate_package_name(package_file)
    )

    # Make sure the directory exists before we start writing files to it
    os.makedirs(os.path.join(get_channel_dir(), platform), exist_ok=True)

    file_name = get_package_file_name(
        package_name, package_version, package_build, file_extension
    )
    file_path = get_package_file_path(get_channel_dir(), platform, file_name)

    def save_uploaded_file():
        # Open a file and write the uploaded content to it
        with atomic_write(file_path, mode="wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

    try:
        await run_in_threadpool(save_uploaded_file)
        return {"message": "Package uploaded successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error writing to file: {str(e)}"
        ) from e
    finally:
        # Always close the file, even if an error occurs
        file.file.close()


@app.delete("/{platform}/{package_file}")
async def delete_package(
    package_file: str,
    platform: str = Path(pattern=PLATFORM_REGEX),
    # api_key: APIKeyHeader = Depends(get_api_key),
):
    # Validate the package file name
    package_name, package_version, package_build, file_extension = (
        validate_package_name(package_file)
    )

    file_name = get_package_file_name(
        package_name, package_version, package_build, file_extension
    )
    file_path = get_package_file_path(get_channel_dir(), platform, file_name)

    # Check if file exists
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    # Remove the file
    os.remove(file_path)
    with suppress(FileNotFoundError):
        os.remove(f"{file_path}.lock")

    return {"message": "Package deleted successfully"}


@app.get("/{platform}/{package_file}/hash/sha256")
async def fetch_sha256(
    package_file: str,
    platform: str = Path(pattern=PLATFORM_REGEX),
):
    # Validate the package file name
    package_name, package_version, package_build, file_extension = (
        validate_package_name(package_file)
    )

    file_name = get_package_file_name(
        package_name, package_version, package_build, file_extension
    )
    file_path = get_package_file_path(get_channel_dir(), platform, file_name)

    # Check if file exists
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    # Calculate the SHA256 hash
    sha256_hash = sha256_in_chunks(file_path)

    return {"sha256": sha256_hash}


@app.get("/{platform}/{package_file}/hash/md5")
async def fetch_md5(
    package_file: str,
    platform: str = Path(pattern=PLATFORM_REGEX),
):
    # Validate the package file name
    package_name, package_version, package_build, file_extension = (
        validate_package_name(package_file)
    )

    file_name = get_package_file_name(
        package_name, package_version, package_build, file_extension
    )
    file_path = get_package_file_path(get_channel_dir(), platform, file_name)

    # Check if file exists
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    # Calculate the MD5 hash
    md5_hash = md5_in_chunks(file_path)

    return {"md5": md5_hash}


@app.get("/{platform}/{filename}")
async def fetch_repodata(filename: str, platform: str = Path(pattern=PLATFORM_REGEX)):
    if not filename in {
        "current_repodata.json",
        "current_repodata.json.bz2",
        "current_repodata.json.zst",
        "repodata.json",
        "repodata.json.bz2",
        "repodata.json.zst",
        "repodata_from_packages.json",
        "repodata_from_packages.json.bz2",
        "repodata_from_packages.json.zst",
        "patch_instructions.json",
        "patch_instructions.json.bz2",
        "patch_instructions.json.zst",
    }:
        raise HTTPException(status_code=404, detail="File not found")

    # Construct the filepath
    file_path = get_package_file_path(get_channel_dir(), platform, filename)

    try:
        # Return the file as a response
        return FileResponse(
            path=file_path, media_type="application/json", filename=filename
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="File not found") from e


@app.get("/channeldata.json")
async def fetch_channeldata(platform: str = Path(pattern=PLATFORM_REGEX)):
    # Construct the filepath
    file_path = get_package_file_path(get_channel_dir(), platform, "channeldata.json")

    try:
        # Return the file as a response
        return FileResponse(
            path=file_path, media_type="application/json", filename="channeldata.json"
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="File not found") from e
