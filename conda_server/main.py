import hashlib
import os
import shutil

from fastapi import Depends, FastAPI, File, HTTPException, Security, UploadFile
from fastapi.responses import FileResponse
from fastapi.security.api_key import APIKeyHeader

from .atomic import atomic_write
from .utils import (
    get_package_file_name,
    get_package_file_path,
    get_server_packages_path,
    validate_file_extension,
    validate_package_build,
    validate_package_name,
    validate_package_version,
    validate_platform,
)

# TODO: implement package indexing mechanism - use `conda index`
# TODO: validate uploaded file is a valid conda package
# TODO: implement authentication - should be configurable for both download and upload
# TODO: add logging
# TODO: implement rate limiting - should be configurable
# TODO: add configurable file size limit
# TODO: configurable timeout (set timeout on filelock)? - might be useful for large uploads
# TODO: implement search endpoints
# TODO: abstract away the file system to make it easier to implement other backing stores - look into fuse and alternatives
# TODO: implement s3 backing store - look into s3fs and alternatives
# TODO: implement postgres backing store - look into dbfs and alternatives


API_KEY = os.getenv("CONDA_SERVER_API_KEY", "secret")
API_KEY_NAME = "X-API-Key"

app = FastAPI()


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
    platform: str,
    package_name: str,
    package_version: str,
    package_build: str,
    file_extension: str,
):
    validate_platform(platform)
    validate_package_name(package_name)
    validate_package_version(package_version)
    validate_package_build(package_build)
    validate_file_extension(file_extension)

    file_name = get_package_file_name(
        package_name, package_version, package_build, file_extension
    )
    file_path = get_package_file_path(get_server_packages_path(), platform, file_name)
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
    platform: str,
    package_name: str,
    package_version: str,
    package_build: str,
    file_extension: str,
    file: UploadFile = File(...),
    api_key: APIKeyHeader = Depends(get_api_key),
):
    validate_platform(platform)
    validate_package_name(package_name)
    validate_package_version(package_version)
    validate_package_build(package_build)
    validate_file_extension(file_extension)

    # Make sure the directory exists before we start writing files to it
    os.makedirs(os.path.join(get_server_packages_path(), platform), exist_ok=True)

    file_name = get_package_file_name(
        package_name, package_version, package_build, file_extension
    )
    file_path = get_package_file_path(get_server_packages_path(), platform, file_name)

    try:
        # Open a file and write the uploaded content to it chunk by chunk
        with atomic_write(file_path, mode="wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error writing to file: {str(e)}"
        ) from e
    finally:
        # Always close the file, even if an error occurs
        file.file.close()

    return {"message": "Package uploaded successfully"}


@app.delete(
    "/{platform}/{package_name}-{package_version}-{package_build}.{file_extension}}"
)
async def delete_package(
    platform: str,
    package_name: str,
    package_version: str,
    package_build: str,
    file_extension: str,
    api_key: APIKeyHeader = Depends(get_api_key),
):
    validate_platform(platform)
    validate_package_name(package_name)
    validate_package_version(package_version)
    validate_package_build(package_build)
    validate_file_extension(file_extension)

    file_name = get_package_file_name(
        package_name, package_version, package_build, file_extension
    )
    file_path = get_package_file_path(get_server_packages_path(), platform, file_name)

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
    platform: str,
    package_name: str,
    package_version: str,
    package_build: str,
    file_extension: str,
):
    validate_platform(platform)
    validate_package_name(package_name)
    validate_package_version(package_version)
    validate_package_build(package_build)
    validate_file_extension(file_extension)

    file_name = get_package_file_name(
        package_name, package_version, package_build, file_extension
    )
    file_path = get_package_file_path(get_server_packages_path(), platform, file_name)

    # Check if file exists
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    # Calculate the SHA-256 hash
    sha256_hash = hashlib.sha256()

    with open(file_path, "rb") as f:
        # Read and update hash string value in blocks of 4K
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)

    return {"sha256": sha256_hash.hexdigest()}


@app.get(
    "/{platform}/{package_name}-{package_version}-{package_build}.{file_extension}/hash/md5"
)
async def fetch_md5(
    platform: str,
    package_name: str,
    package_version: str,
    package_build: str,
    file_extension: str,
):
    validate_platform(platform)
    validate_package_name(package_name)
    validate_package_version(package_version)
    validate_package_build(package_build)
    validate_file_extension(file_extension)

    file_name = get_package_file_name(
        package_name, package_version, package_build, file_extension
    )
    file_path = get_package_file_path(get_server_packages_path(), platform, file_name)

    # Check if file exists
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    # Calculate the MD5 hash
    md5_hash = hashlib.md5()

    with open(file_path, "rb") as f:
        # Read and update hash string value in blocks of 4K
        for byte_block in iter(lambda: f.read(4096), b""):
            md5_hash.update(byte_block)

    return {"md5": md5_hash.hexdigest()}


@app.get("/{platform}/{filename}.json")
async def fetch_repodata(platform: str, filename: str):
    validate_platform(platform)
    if not filename in {"repodata", "repodata_from_packages", "patch_instructions"}:
        raise HTTPException(status_code=404, detail="File not found")

    # Construct the filepath
    file_path = get_package_file_path(
        get_server_packages_path(), platform, f"{filename}.json"
    )

    try:
        # Return the file as a response
        return FileResponse(
            path=file_path, media_type="application/json", filename=f"{filename}.json"
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="File not found") from e


@app.get("/channeldata.json")
async def fetch_channeldata(platform: str):
    validate_platform(platform)

    # Construct the filepath
    file_path = get_package_file_path(
        get_server_packages_path(), platform, "channeldata.json"
    )

    try:
        # Return the file as a response
        return FileResponse(
            path=file_path, media_type="application/json", filename="channeldata.json"
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="File not found") from e


@app.on_event("startup")
async def startup_event():
    # Create the packages directory if it doesn't exist
    os.makedirs(get_server_packages_path(), exist_ok=True)

    # TODO: use `conda index` to generate the index files
    # https://docs.conda.io/projects/conda-build/en/stable/concepts/generating-index.html
