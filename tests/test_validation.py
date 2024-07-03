import os

import pytest
from fastapi import HTTPException


@pytest.mark.parametrize(
    "package_name, expected",
    [
        ("testpkg-0.0.1-py311_0.tar.bz2", ("testpkg", "0.0.1", "py311_0", "tar.bz2")),
        ("test_pkg-0.0.1-py311_0.tar.bz2", ("test_pkg", "0.0.1", "py311_0", "tar.bz2")),
        ("test.pkg-0.0.1-py311_0.tar.bz2", ("test.pkg", "0.0.1", "py311_0", "tar.bz2")),
        ("test-pkg-0.0.1-py311_0.tar.bz2", ("test-pkg", "0.0.1", "py311_0", "tar.bz2")),
        ("t3stpkg-0.0.1-py311_0.tar.bz2", ("t3stpkg", "0.0.1", "py311_0", "tar.bz2")),
        (
            "test-pkg-0.0.1+alpha-py311_0.tar.bz2",
            ("test-pkg", "0.0.1+alpha", "py311_0", "tar.bz2"),
        ),
        (
            "testpkg-0.0.1+alpha-py311_0.tar.bz2",
            ("testpkg", "0.0.1+alpha", "py311_0", "tar.bz2"),
        ),
        (
            "testpkg-0.0.1+alpha.1-py311_0.tar.bz2",
            ("testpkg", "0.0.1+alpha.1", "py311_0", "tar.bz2"),
        ),
        (
            "testpkg-0.0.1+20240605140000-py311_0.tar.bz2",
            ("testpkg", "0.0.1+20240605140000", "py311_0", "tar.bz2"),
        ),
        ("testpkg-0.0.1-py311_0.conda", ("testpkg", "0.0.1", "py311_0", "conda")),
        ("te$tpkg-0.0.1-py311_0.tar.bz2", HTTPException),
        ("testpkg-0.1-py311_0.tar.bz2", HTTPException),
        ("testpkg-0.1.-py311_0.tar.bz2", HTTPException),
        ("testpkg-0..1-py311_0.tar.bz2", HTTPException),
        ("testpkg-0.a.1-py311_0.tar.bz2", HTTPException),
        ("testpkg-0.0.1.0-py311_0.tar.bz2", HTTPException),
        ("testpkg-00.0.1-py311_0.tar.bz2", HTTPException),
        ("testpkg-0.0.1--py311_0.tar.bz2", HTTPException),
        ("testpkg-0.0.1+-py311_0.tar.bz2", HTTPException),
        ("testpkg-0.0.1-alpha.-py311_0.tar.bz2", HTTPException),
        ("testpkg-0.0.1+20240605140000!-py311_0.tar.bz2", HTTPException),
        ("testpkg-v0.0.1-py311_0.tar.bz2", HTTPException),
        ("testpkg-0.0.1-py311_0.zip", HTTPException),
    ],
)
def test_validate_package_name(package_name, expected):
    current_use_semver = os.getenv("CONDA_SERVER_USE_SEMVER")
    os.environ["CONDA_SERVER_USE_SEMVER"] = "1"
    from conda_server.validation import validate_package_name

    try:
        if isinstance(expected, tuple):
            assert validate_package_name(package_name) == expected
        else:
            with pytest.raises(HTTPException):
                validate_package_name(package_name)
    finally:
        if current_use_semver is not None:
            os.environ["CONDA_SERVER_USE_SEMVER"] = current_use_semver
        else:
            del os.environ["CONDA_SERVER_USE_SEMVER"]
