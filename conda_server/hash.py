import hashlib


def sha256_in_chunks(file_path: str, chunk_size=4096) -> str:
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read and update hash string value in blocks of 4K
        for byte_block in iter(lambda: f.read(chunk_size), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def md5_in_chunks(file_path: str, chunk_size=4096) -> str:
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        # Read and update hash string value in blocks of 4K
        for byte_block in iter(lambda: f.read(chunk_size), b""):
            md5_hash.update(byte_block)
    return md5_hash.hexdigest()
