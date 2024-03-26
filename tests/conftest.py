import pytest
from .build_package import build_fake_package
import glob
import shutil
from pathlib import Path


@pytest.fixture
def testpkg():
    # Check if the package is already in the tests directory
    if glob.glob(r"tests/testpkg-*.tar.bz2"):
        return

    # Build a fake package with conda-build and return its path
    package_path = build_fake_package()

    # Copy the package to the tests directory
    shutil.copy(package_path, Path.cwd() / "tests")
