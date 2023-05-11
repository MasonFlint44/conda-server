import functools
import json
import os
import re

from fastapi import HTTPException

from .atomic import atomic_write

_package_name_regex = re.compile(r"^[a-z][a-z0-9_]*$")
_package_version_regex = re.compile(
    r"^(\d+\.\d+\.\d+)(?:[a-zA-Z-][0-9a-zA-Z-]*(?:\.[0-9a-zA-Z-]*)*)?$"
)
_package_build_regex = re.compile(r"^\d+[a-zA-Z0-9_.]*$")
_platform_regex = re.compile(
    r"^(linux-32|linux-64|linux-armv6l|linux-armv7l|linux-aarch64|osx-64|osx-arm64|win-32|win-64|noarch)$"
)


def validate_package_name(package_name: str) -> None:
    if not _package_name_regex.match(package_name):
        raise HTTPException(status_code=400, detail="Invalid package name")


def validate_package_version(package_version: str) -> None:
    if not _package_version_regex.match(package_version):
        raise HTTPException(status_code=400, detail="Invalid package version")


def validate_package_build(package_build: str) -> None:
    if not _package_build_regex.match(package_build):
        raise HTTPException(status_code=400, detail="Invalid package build")


def validate_platform(platform: str) -> None:
    if not _platform_regex.match(platform):
        raise HTTPException(status_code=400, detail="Invalid package platform")


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
