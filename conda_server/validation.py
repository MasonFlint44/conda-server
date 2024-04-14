import re

from fastapi import HTTPException
from .utils import get_platforms

PLATFORM_REGEX = rf"^({'|'.join(get_platforms())})$"
PACKAGE_NAME_REGEX = re.compile(r"^[a-z0-9_.-]+$")
# https://semver.org/#is-there-a-suggested-regular-expression-regex-to-check-a-semver-string
PACKAGE_VERSION_REGEX = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)
PACKAGE_BUILD_REGEX = re.compile(r"^[a-z0-9_]+$")
FILE_EXTENSION_REGEX = re.compile(r"^(tar\.bz2|conda)$")


def validate_package_name(filename: str) -> tuple[str, str, str, str]:
    package_name, package_version, package_build = filename.split("-", maxsplit=2)
    package_build, file_extension = package_build.split(".", maxsplit=1)

    if (
        not PACKAGE_NAME_REGEX.match(package_name)
        or not PACKAGE_VERSION_REGEX.match(package_version)
        or not PACKAGE_BUILD_REGEX.match(package_build)
        or not FILE_EXTENSION_REGEX.match(file_extension)
    ):
        raise HTTPException(status_code=400, detail="Invalid package file name format")

    return package_name, package_version, package_build, file_extension
