import asyncio
import os
import shutil
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, HTTPException, Path, Security, UploadFile
from fastapi.responses import FileResponse
from fastapi.security.api_key import APIKeyHeader

from .atomic import atomic_write
from .utils import (
    FILE_EXTENSION_REGEX,
    PACKAGE_BUILD_REGEX,
    PACKAGE_NAME_REGEX,
    PACKAGE_VERSION_REGEX,
    PLATFORM_REGEX,
    get_package_file_name,
    get_package_file_path,
    get_channel_dir,
    get_platforms,
)
from .hash import md5_in_chunks, sha256_in_chunks
from .index import IndexManager
from fastapi.concurrency import run_in_threadpool
from concurrent.futures import ProcessPoolExecutor

# TODO: implement package indexing mechanism - use `conda index`
# TODO: validate uploaded file is a valid conda package - at least validate platform
# TODO: implement authentication - should be configurable for both download and upload
# TODO: add logging
# TODO: implement rate limiting - should be configurable
# TODO: add configurable file size limit
# TODO: implement search endpoints
# TODO: abstract away the file system to make it easier to implement other backing stores - look into fuse and alternatives
# TODO: implement s3 backing store - look into s3fs and alternatives
# TODO: implement postgres backing store - look into dbfs and alternatives
# TODO: use file watcher to trigger index generation
# TODO: watch for changes in channel directory using watchfiles and trigger index generation

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

    # Start watching the channel directory for changes
    index_manager.watch_channel_dir()

    with process_pool_executor:
        yield

    # Stop watching the channel directory for changes
    index_manager.stop_watching()


process_pool_executor = ProcessPoolExecutor()
app = FastAPI(lifespan=lifespan)
loop = asyncio.get_event_loop()
index_manager = IndexManager()

def get_api_key(
    api_key_header: str = Security(APIKeyHeader(name=API_KEY_NAME)),
):
    if api_key_header == API_KEY:
        return api_key_header
    raise HTTPException(status_code=400, detail="API Key was not provided")


@app.get(
    "/{platform}/{package_name}-{package_version}-{package_build}.{file_extension}"
)
async def fetch_package(
    platform: str = Path(pattern=PLATFORM_REGEX),
    package_name: str = Path(pattern=PACKAGE_NAME_REGEX),
    package_version: str = Path(pattern=PACKAGE_VERSION_REGEX),
    package_build: str = Path(pattern=PACKAGE_BUILD_REGEX),
    file_extension: str = Path(pattern=FILE_EXTENSION_REGEX),
):
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


@app.put(
    "/{platform}/{package_name}-{package_version}-{package_build}.{file_extension}"
)
async def upload_package(
    platform: str = Path(pattern=PLATFORM_REGEX),
    package_name: str = Path(pattern=PACKAGE_NAME_REGEX),
    package_version: str = Path(pattern=PACKAGE_VERSION_REGEX),
    package_build: str = Path(pattern=PACKAGE_BUILD_REGEX),
    file_extension: str = Path(pattern=FILE_EXTENSION_REGEX),
    file: UploadFile = File(...),
    api_key: APIKeyHeader = Depends(get_api_key),
):
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


@app.delete(
    "/{platform}/{package_name}-{package_version}-{package_build}.{file_extension}"
)
async def delete_package(
    platform: str = Path(pattern=PLATFORM_REGEX),
    package_name: str = Path(pattern=PACKAGE_NAME_REGEX),
    package_version: str = Path(pattern=PACKAGE_VERSION_REGEX),
    package_build: str = Path(pattern=PACKAGE_BUILD_REGEX),
    file_extension: str = Path(pattern=FILE_EXTENSION_REGEX),
    api_key: APIKeyHeader = Depends(get_api_key),
):
    file_name = get_package_file_name(
        package_name, package_version, package_build, file_extension
    )
    file_path = get_package_file_path(get_channel_dir(), platform, file_name)

    # Check if file exists
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    # Remove the file
    os.remove(file_path)
    os.remove(f"{file_path}.lock")

    return {"message": "Package deleted successfully"}


@app.get(
    "/{platform}/{package_name}-{package_version}-{package_build}.{file_extension}/hash/sha256"
)
async def fetch_sha256(
    platform: str = Path(pattern=PLATFORM_REGEX),
    package_name: str = Path(pattern=PACKAGE_NAME_REGEX),
    package_version: str = Path(pattern=PACKAGE_VERSION_REGEX),
    package_build: str = Path(pattern=PACKAGE_BUILD_REGEX),
    file_extension: str = Path(pattern=FILE_EXTENSION_REGEX),
):
    file_name = get_package_file_name(
        package_name, package_version, package_build, file_extension
    )
    file_path = get_package_file_path(get_channel_dir(), platform, file_name)

    # Check if file exists
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    # Calculate the SHA256 hash
    sha256_hash = await loop.run_in_executor(
        process_pool_executor, sha256_in_chunks, file_path
    )

    return {"sha256": sha256_hash}


@app.get(
    "/{platform}/{package_name}-{package_version}-{package_build}.{file_extension}/hash/md5"
)
async def fetch_md5(
    platform: str = Path(pattern=PLATFORM_REGEX),
    package_name: str = Path(pattern=PACKAGE_NAME_REGEX),
    package_version: str = Path(pattern=PACKAGE_VERSION_REGEX),
    package_build: str = Path(pattern=PACKAGE_BUILD_REGEX),
    file_extension: str = Path(pattern=FILE_EXTENSION_REGEX),
):
    file_name = get_package_file_name(
        package_name, package_version, package_build, file_extension
    )
    file_path = get_package_file_path(get_channel_dir(), platform, file_name)

    # Check if file exists
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    # Calculate the MD5 hash
    md5_hash = await loop.run_in_executor(
        process_pool_executor, md5_in_chunks, file_path
    )

    return {"md5": md5_hash}


# TODO: are repodata_from_packages or patch_instructions necessary?
# TODO: do we need to support repodata.json.bz2?
@app.get("/{platform}/{filename}.json")
async def fetch_repodata(filename: str, platform: str = Path(pattern=PLATFORM_REGEX)):
    if not filename in {"repodata", "repodata_from_packages", "patch_instructions"}:
        raise HTTPException(status_code=404, detail="File not found")

    # Construct the filepath
    file_path = get_package_file_path(get_channel_dir(), platform, f"{filename}.json")

    try:
        # Return the file as a response
        return FileResponse(
            path=file_path, media_type="application/json", filename=f"{filename}.json"
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
