from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
import pytest
import glob
import shutil
from pathlib import Path
from os.path import basename
from .build_package import build_fake_package


@pytest.fixture(autouse=True, scope="session")
def testpkg() -> Path:
    # Check if the package is already in the tests directory
    matches = glob.glob(r"tests/testpkg-*.tar.bz2")
    if matches:
        # Return the path to the package
        return Path.cwd() / matches[0]

    # Build a fake package with conda-build and return its path
    package_path = build_fake_package()

    # Copy the package to the tests directory
    tests_dir = Path.cwd() / "tests"
    shutil.copy(package_path, tests_dir)

    # Return the path to the package
    return tests_dir / basename(package_path)


@pytest.fixture(scope="session")
async def async_client():
    from conda_server.main import app

    async with AsyncClient(
        transport=ASGITransport(app), base_url="http://test"
    ) as client, LifespanManager(app):
        yield client


@pytest.fixture(autouse=True, scope="session")
def anyio_backend(request):
    return "asyncio", {"use_uvloop": True}
