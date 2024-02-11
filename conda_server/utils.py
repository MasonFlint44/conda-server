import functools
import os


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


PACKAGE_NAME_REGEX = r"^[a-z0-9_.-]+$"
# https://semver.org/#is-there-a-suggested-regular-expression-regex-to-check-a-semver-string
PACKAGE_VERSION_REGEX = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
PACKAGE_BUILD_REGEX = r"^[a-z0-9_]+$"
PLATFORM_REGEX = rf"^({'|'.join(get_platforms())})$"
FILE_EXTENSION_REGEX = r"^(tar\.bz2|conda)$"


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
