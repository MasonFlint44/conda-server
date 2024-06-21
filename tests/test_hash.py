from pathlib import Path

from conda_server.hash import md5_in_chunks, sha256_in_chunks


def test_sha256_in_chunks(testpkg: Path):
    assert (
        sha256_in_chunks(str(testpkg))
        == "4b8561fe7c20ff2cc8f58c4efbc1cb1102e4fe559fbafbe1bc564ec33134d3da"
    )


def test_md5_in_chunks(testpkg: Path):
    assert md5_in_chunks(str(testpkg)) == "09cd4ce1cd95df5982ac45e8ac4ae5f5"
