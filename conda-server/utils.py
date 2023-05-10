import functools
import json
import os
import shutil
import tempfile
from contextlib import contextmanager


@functools.lru_cache
def get_package_file_name(
    package_name: str, package_version: str, package_build: str
) -> str:
    return f"{package_name}-{package_version}-{package_build}.tar.bz2"


@functools.lru_cache
def get_package_file_path(packages: str, platform: str, file_name: str) -> str:
    return os.path.join(packages, platform, file_name)


def get_server_packages() -> str:
    return os.getenv("CONDA_SERVER_PACKAGES", "packages")


def remove_package_from_json(
    platform: str,
    package_name: str,
    package_version: str,
    package_build: str,
    data_file: str,
) -> None:
    file_path = get_package_file_path(get_server_packages(), platform, data_file)
    if not os.path.isfile(file_path):
        return
    with atomic_write(file_path, encoding="utf-8") as f:
        data = json.load(f)
        data["packages"] = [
            package
            for package in data["packages"]
            if not (
                package["name"] == package_name
                and package["version"] == package_version
                and package["build"] == package_build
            )
        ]
        f.seek(0)
        json.dump(data, f)
        f.truncate()


def add_package_to_json(
    platform: str,
    package_name: str,
    package_version: str,
    package_build: str,
    data_file: str,
) -> None:
    file_path = get_package_file_path(get_server_packages(), platform, data_file)
    if not os.path.isfile(file_path):
        return
    with atomic_write(file_path, encoding="utf-8") as f:
        data = json.load(f)
        if any(
            package["name"] == package_name
            and package["version"] == package_version
            and package["build"] == package_build
            for package in data["packages"]
        ):
            return
        data["packages"].append(
            {
                "name": package_name,
                "version": package_version,
                "build": package_build,
            }
        )
        f.seek(0)
        json.dump(data, f)
        f.truncate()


@contextmanager
def atomic_write(path, encoding="utf-8"):
    # Open a temporary file in the same directory as the original file
    temp_file = tempfile.NamedTemporaryFile(
        "w", dir=os.path.dirname(path), delete=False, encoding=encoding
    )
    temp_path = temp_file.name

    # If the file already exists, copy its content to the temporary file
    if os.path.exists(path):
        with open(path, "r", encoding=encoding) as original_file:
            shutil.copyfileobj(original_file, temp_file)
        # move back to the beginning of the temp file so the user can read from the start
        temp_file.seek(0)

    try:
        yield temp_file  # This is the file that the user will interact with
    except:
        # If there was an exception, remove the temp file and re-raise the exception
        temp_file.close()
        os.remove(temp_path)
        raise
    else:
        # Ensure all buffered outputs are flushed to the disk
        temp_file.flush()
        os.fsync(temp_file.fileno())
        temp_file.close()

        # If there were no exceptions, replace the original file
        os.replace(temp_path, path)
