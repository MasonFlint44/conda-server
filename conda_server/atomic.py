import os
import shutil
import tempfile
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import BinaryIO, ContextManager, Literal, TextIO, overload

from filelock import FileLock

from ._types import OpenBinaryMode, OpenTextMode


@overload
def atomic_write(
    path: str, mode: Literal[OpenTextMode] | None = "w", encoding: str | None = "utf-8"
) -> ContextManager[TextIO]: ...


@overload
def atomic_write(
    path: str, mode: Literal[OpenBinaryMode], encoding: str | None = None
) -> ContextManager[BinaryIO]: ...


@contextmanager
def atomic_write(path: str, mode="w", encoding=None):
    """
    Atomically write a file.
    Protects against partial reads and writes, and ensures that the file
    is either fully written or not written at all. Creates a lock file to
    prevent other processes using this function from writing to the same
    file concurrently.
    """

    if mode in {"r", "rb"}:
        raise ValueError("File mode 'r' not allowed. Must be writable.")

    try:
        # Acquire a lock to prevent concurrent writes to the same file
        with FileLock(f"{path}.lock") as file_lock:
            # Create a temporary file in the same directory as the target file
            temp_file = tempfile.NamedTemporaryFile(
                mode,
                encoding=encoding,
                suffix=".tmp",
                dir=os.path.dirname(path),
                delete=False,
            )
            temp_path = temp_file.name

            # If the file already exists, preserve its content by copying it to the temporary file.
            # If the file is opened in write mode, the file is truncated and there is no need to
            # copy the content.
            if os.path.exists(path) and "w" not in mode:
                read_mode = "rb" if "b" in mode else "r"
                with open(path, read_mode, encoding=encoding) as original_file:
                    shutil.copyfileobj(original_file, temp_file)

                # If the file is not opened in append mode, reset the file position to the
                # beginning of the file.
                if mode not in {"a", "ab", "a+", "ab+"}:
                    temp_file.seek(0)

            # Yield the temporary file for the user to write data
            yield temp_file

            # Flush and sync the file to ensure all data is written to disk
            if not temp_file.closed:
                temp_file.flush()
                os.fsync(temp_file.fileno())
            temp_file.close()

            # Atomically replace the target file with the temporary file
            os.replace(temp_path, path)
    finally:
        # Close and remove the temporary file and lock file
        temp_file.close()
        safely_remove_lock_file(f"{path}.lock")
        try:
            os.remove(temp_path)
        except FileNotFoundError:
            pass


def safely_remove_lock_file(lock_file_path: str):
    lock_file = Path(lock_file_path)

    # Ensure the lock file exists before attempting to stat it
    if not lock_file.exists():
        return

    # Open the lock file and get its inode
    with open(lock_file_path, "rb") as fd:
        st0 = os.fstat(fd.fileno())

    # Check inode consistency
    st1 = lock_file.stat()
    if st0.st_ino != st1.st_ino:
        # Inode mismatch. File will not be removed.
        return

    # Inode matches, safe to remove the file
    with suppress(FileNotFoundError):
        lock_file.unlink()
