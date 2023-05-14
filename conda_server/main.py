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
    create_json_file,
    get_package_file_name,
    get_package_file_path,
    get_platforms,
    get_server_packages_path,
    remove_package_from_json,
    validate_package_build,
    validate_package_name,
    validate_package_version,
    validate_platform,
)

# TODO: nothing creates the repodata.json and channeldata.json files if they don't exist
# TODO: validate uploaded file is a valid .tar.bz2 file
# TODO: validate uploaded file is a valid conda package
# TODO: implement authentication
# TODO: implement logging
# TODO: implement rate limiting - should be configurable
# TODO: might move writing to JSON files to a separate thread or process
# TODO: add configurable file size limit
# TODO: configurable timeout (set timeout on filelock)? - might be useful for large uploads
# TODO: implement search endpoints
# TODO: abstract away the file system to make it easier to implement other backing stores
# TODO: implement s3 backing store
# TODO: implement postgres backing store


API_KEY = os.getenv("CONDA_SERVER_API_KEY", "secret")
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
    file_path = get_package_file_path(get_server_packages_path(), platform, file_name)

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
    file: UploadFile = File(...),
    api_key: APIKeyHeader = Depends(get_api_key),
):
    validate_platform(platform)
    validate_package_name(package_name)
    validate_package_version(package_version)
    validate_package_build(package_build)

    try:
        # Make sure the directory exists before we start writing files to it
        os.makedirs(os.path.join(get_server_packages_path(), platform), exist_ok=True)

        file_name = get_package_file_name(package_name, package_version, package_build)
        file_path = get_package_file_path(
            get_server_packages_path(), platform, file_name
        )

        try:
            # Open a file and write the uploaded content to it chunk by chunk
            with atomic_write(file_path, mode="wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error writing to file: {str(e)}"
            ) from e

        try:
            # Open repodata.json and channeldata.json and add the new package
            add_package_to_json(
                platform, package_name, package_version, package_build, "repodata.json"
            )
            add_package_to_json(
                platform,
                package_name,
                package_version,
                package_build,
                "channeldata.json",
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error updating JSON files: {str(e)}"
            ) from e

    finally:
        # Always close the file, even if an error occurs
        file.file.close()

    return {"message": "Package uploaded successfully"}


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
    file_path = get_package_file_path(get_server_packages_path(), platform, file_name)

    # Check if file exists
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    # Remove the file
    os.remove(file_path)
    os.remove(f"{file_path}.lock")

    # Open repodata.json and channeldata.json and remove the deleted package
    remove_package_from_json(
        platform, package_name, package_version, package_build, "repodata.json"
    )
    remove_package_from_json(
        platform, package_name, package_version, package_build, "channeldata.json"
    )

    return {"message": "Package deleted successfully"}


# TODO: is this endpoint necessary?
@app.get("/{platform}/{package_name}-{package_version}-{package_build}.tar.bz2.sha256")
async def fetch_sha256(
    platform: str, package_name: str, package_version: str, package_build: str
):
    validate_platform(platform)
    validate_package_name(package_name)
    validate_package_version(package_version)
    validate_package_build(package_build)

    file_name = get_package_file_name(package_name, package_version, package_build)
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


@app.get("/{platform}/repodata.json")
async def fetch_repodata(platform: str):
    validate_platform(platform)

    # Construct the filepath
    file_path = get_package_file_path(
        get_server_packages_path(), platform, "repodata.json"
    )

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
        get_server_packages_path(), platform, "channeldata.json"
    )

    # Check if file exists
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    # Read the JSON file
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Return the data as a JSON response
    return JSONResponse(content=data)


@app.on_event("startup")
async def startup_event():
    # Create the packages directory if it doesn't exist
    os.makedirs(get_server_packages_path(), exist_ok=True)

    # Create the repodata.json and channeldata.json files if they don't exist
    for platform in get_platforms():
        # TODO: create platform directories if they don't exist
        create_json_file(
            os.path.join(get_server_packages_path(), platform, "repodata.json")
        )
    create_json_file(os.path.join(get_server_packages_path(), "channeldata.json"))

    # TODO: are there also root repodata.json and channeldata.json files that need to be created?

    # TODO: need to adjust logic to handle correct file structure. It should look like this:
    #   - packages
    #       - linux-64
    #           - package_name-version-build.tar.bz2
    #           - package_name-version-build.tar.bz2.lock
    #           - repodata.json
    #           - repodata.json.bz2
    #           - repodata_from_packages.json
    #           - repodata_from_packages.json.bz2
    #       - osx-64
    #           - package_name-version-build.tar.bz2
    #           - package_name-version-build.tar.bz2.lock
    #           - repodata.json
    #           - repodata.json.bz2
    #           - repodata_from_packages.json
    #           - repodata_from_packages.json.bz2
    #       - other platforms
    #           - ...
    #   - channeldata.json
    #   - rss.xml

    # TODO: should we use `conda index` to generate the repodata.json files?
    # https://docs.conda.io/projects/conda-build/en/3.21.x/concepts/generating-index.html
