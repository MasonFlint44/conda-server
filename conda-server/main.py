import hashlib
import json
import os
import shutil

from fastapi import Depends, FastAPI, File, HTTPException, Security, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security.api_key import APIKeyHeader

from .atomic import atomic_write
from .utils import (
    add_package_to_json,
    get_package_file_name,
    get_package_file_path,
    get_server_packages,
    remove_package_from_json,
    validate_package_build,
    validate_package_name,
    validate_package_version,
    validate_platform,
)

# TODO: implement authentication
# TODO: implement logging
# TODO: implement rate limiting - should be configurable
# TODO: might move writing to JSON files to a separate thread or process
# TODO: add configurable file size limit
# TODO: configurable timeout? - might be useful for large uploads
# TODO: implement search endpoints
# TODO: abstract away the file system to make it easier to implement other backing stores
# TODO: implement s3 backing store
# TODO: implement postgres backing store


API_KEY = os.getenv("CONDA_SERVER_API_KEY")
API_KEY_NAME = "X-API-Key"

app = FastAPI()


def get_api_key(
    api_key_header: str = Security(APIKeyHeader(name=API_KEY_NAME)),
):
    if api_key_header == API_KEY:
        return api_key_header
    raise HTTPException(status_code=400, detail="API Key was not provided")


@app.get("/{platform}/{package_name}-{package_version}-{package_build}.tar.bz2")
async def fetch_package(
    platform: str, package_name: str, package_version: str, package_build: str
):
    validate_platform(platform)
    validate_package_name(package_name)
    validate_package_version(package_version)
    validate_package_build(package_build)

    file_name = get_package_file_name(package_name, package_version, package_build)
    file_path = get_package_file_path(get_server_packages(), platform, file_name)

    # Check if file exists
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    # Return the file as a response
    return FileResponse(
        path=file_path,
        media_type="application/x-bzip2",
        filename=file_name,
    )


@app.put("/{platform}/{package_name}-{package_version}-{package_build}.tar.bz2")
async def upload_package(
    platform: str,
    package_name: str,
    package_version: str,
    package_build: str,
    file_: UploadFile = File(...),
    api_key: APIKeyHeader = Depends(get_api_key),
):
    validate_platform(platform)
    validate_package_name(package_name)
    validate_package_version(package_version)
    validate_package_build(package_build)

    try:
        # Make sure the directory exists before we start writing files to it
        os.makedirs(os.path.join(get_server_packages(), platform), exist_ok=True)

        file_name = get_package_file_name(package_name, package_version, package_build)
        file_path = get_package_file_path(get_server_packages(), platform, file_name)

        # TODO: handle if an error occurs while writing to the file
        # Open a file and write the uploaded content to it chunk by chunk
        with atomic_write(file_path, mode="wb") as buffer:
            shutil.copyfileobj(file_.file, buffer)

        # Open repodata.json and channeldata.json and add the new package
        add_package_to_json(
            platform, package_name, package_version, package_build, "repodata.json"
        )
        add_package_to_json(
            platform, package_name, package_version, package_build, "channeldata.json"
        )

    finally:
        # Always close the file, even if an error occurs
        file_.file.close()

    return {"message": "File uploaded successfully"}


@app.delete("/{platform}/{package_name}-{package_version}-{package_build}.tar.bz2")
async def delete_package(
    platform: str,
    package_name: str,
    package_version: str,
    package_build: str,
    api_key: APIKeyHeader = Depends(get_api_key),
):
    validate_platform(platform)
    validate_package_name(package_name)
    validate_package_version(package_version)
    validate_package_build(package_build)

    file_name = get_package_file_name(package_name, package_version, package_build)
    file_path = get_package_file_path(get_server_packages(), platform, file_name)

    # Check if file exists
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    # Remove the file
    os.remove(file_path)

    # Open repodata.json and channeldata.json and remove the deleted package
    remove_package_from_json(
        platform, package_name, package_version, package_build, "repodata.json"
    )
    remove_package_from_json(
        platform, package_name, package_version, package_build, "channeldata.json"
    )

    return {"message": "File deleted successfully"}


@app.get("/{platform}/{package_name}-{package_version}-{package_build}.tar.bz2.sha256")
async def fetch_sha256(
    platform: str, package_name: str, package_version: str, package_build: str
):
    validate_platform(platform)
    validate_package_name(package_name)
    validate_package_version(package_version)
    validate_package_build(package_build)

    file_name = get_package_file_name(package_name, package_version, package_build)
    file_path = get_package_file_path(get_server_packages(), platform, file_name)

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


@app.get("/{platform}/repodata.json")
async def fetch_repodata(platform: str):
    validate_platform(platform)

    # Construct the filepath
    file_path = get_package_file_path(get_server_packages(), platform, "repodata.json")

    # Check if file exists
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    # Read the JSON file
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Return the data as a JSON response
    return JSONResponse(content=data)


@app.get("/{platform}/channeldata.json")
async def fetch_channeldata(platform: str):
    validate_platform(platform)

    # Construct the filepath
    file_path = get_package_file_path(
        get_server_packages(), platform, "channeldata.json"
    )

    # Check if file exists
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    # Read the JSON file
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Return the data as a JSON response
    return JSONResponse(content=data)
