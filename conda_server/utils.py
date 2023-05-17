import functools
import os
import re

from fastapi import HTTPException


@functools.lru_cache(maxsize=1)
def get_platforms() -> set[str]:
    return {
        "linux-32",
        "linux-64",
        "linux-aarch64",
        "linux-armv6l",
        "linux-armv7l",
        "linux-ppc64",
        "linux-ppc64le",
        "linux-s390x",
        "noarch",
        "osx-64",
        "osx-arm64",
        "win-32",
        "win-64",
        "win-arm64",
        "zos-z",
    }


_package_name_regex = re.compile(r"^[a-z0-9_.-]+$")
# https://semver.org/#is-there-a-suggested-regular-expression-regex-to-check-a-semver-string
_package_version_regex = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)
_package_build_regex = re.compile(r"^[a-z0-9_]+$")
_platform_regex = re.compile(rf"^({'|'.join(get_platforms())})$")
_file_extension_regex = re.compile(r"^(tar\.bz2|conda)$")


def validate_package_name(package_name: str) -> None:
    if not _package_name_regex.match(package_name):
        raise HTTPException(
            status_code=400,
            detail="Invalid package name - see https://docs.conda.io/projects/conda-build/en/latest/concepts/package-naming-conv.html#package-naming-conventions",
        )


def validate_package_version(package_version: str) -> None:
    if not _package_version_regex.match(package_version):
        raise HTTPException(
            status_code=400, detail="Invalid package version - see https://semver.org/"
        )


def validate_package_build(package_build: str) -> None:
    if not _package_build_regex.match(package_build):
        raise HTTPException(status_code=400, detail="Invalid package build")


def validate_platform(platform: str) -> None:
    if not _platform_regex.match(platform):
        raise HTTPException(status_code=400, detail="Unsupported package platform")


def validate_file_extension(file_extension: str) -> None:
    if not _file_extension_regex.match(file_extension):
        raise HTTPException(status_code=400, detail="Unsupported file extension")


@functools.lru_cache
def get_package_file_name(
    package_name: str, package_version: str, package_build: str, file_extension: str
) -> str:
    return f"{package_name}-{package_version}-{package_build}.{file_extension}"


@functools.lru_cache
def get_package_file_path(packages: str, platform: str, file_name: str) -> str:
    return os.path.join(packages, platform, file_name)


def get_server_packages_path() -> str:
    return os.getenv("CONDA_SERVER_PACKAGES_PATH", "packages")
