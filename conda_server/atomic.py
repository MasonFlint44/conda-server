import os
import shutil
import tempfile
from contextlib import contextmanager
from typing import BinaryIO, ContextManager, Literal, TextIO, overload

from filelock import FileLock

from ._types import OpenBinaryMode, OpenTextMode


@overload
def atomic_write(
    path: str, mode: Literal[OpenTextMode] | None = "w", encoding: str | None = "utf-8"
) -> ContextManager[TextIO]:
    ...


@overload
def atomic_write(
    path: str, mode: Literal[OpenBinaryMode], encoding: str | None = None
) -> ContextManager[BinaryIO]:
    ...


@contextmanager
def atomic_write(path, mode="w", encoding=None):
    with FileLock(f"{path}.lock") as lock:
        # Open a temporary file in the same directory as the original file
        # TODO: could we use SpooledTemporaryFile here?
        temp_file = tempfile.NamedTemporaryFile(
            mode, dir=os.path.dirname(path), delete=False, encoding=encoding
        )
        temp_path = temp_file.name

        try:
            # If the file already exists, copy its content to the temporary file
            if os.path.exists(path):
                read_mode = "rb" if "b" in mode else "r"
                with open(path, read_mode, encoding=encoding) as original_file:
                    shutil.copyfileobj(original_file, temp_file)
                # TODO: don't seek back to the beginning if the file is opened in append mode
                # move back to the beginning of the temp file so the user can read from the start
                temp_file.seek(0)

            # This is the file that the user will interact with
            yield temp_file

            # Ensure all buffered outputs are flushed to the disk
            temp_file.flush()
            os.fsync(temp_file.fileno())
            temp_file.close()

            # Atomically replace the original file with the temp file
            os.replace(temp_path, path)
        finally:
            # Remove the temp file if it still exists
            temp_file.close()
            try:
                os.remove(temp_path)
            except FileNotFoundError:
                pass
