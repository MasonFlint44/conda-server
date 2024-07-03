from pathlib import Path

from conda_server.hash import md5_in_chunks, sha256_in_chunks


def test_sha256_in_chunks(testpkg: Path):
    assert (
        sha256_in_chunks(str(testpkg))
        == "f74353fc376dd8732662cde39e0103080cb7e03c6df4e13a6efa21cd484c48f6"
    )


def test_md5_in_chunks(testpkg: Path):
    assert md5_in_chunks(str(testpkg)) == "ec370971727ce7870eba47f8ad2847ba"
