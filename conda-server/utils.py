import functools
import json
import os

from .atomic import atomic_write


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
    with atomic_write(file_path) as f:
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
    with atomic_write(file_path) as f:
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
