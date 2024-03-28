from pathlib import Path
from os.path import basename
from httpx import AsyncClient


async def test_upload(testpkg: Path, async_client: AsyncClient):
    # Upload the package to the server
    with open(testpkg, "rb") as f:
        response = await async_client.put(
            f"/linux-64/{basename(testpkg)}", files={"file": f}
        )
    assert response.status_code == 200

    # # Check that the package is in the server's package list
    # response = await async_client.get("/packages")
    # assert response.status_code == 200
    # assert testpkg.name in response.json()
