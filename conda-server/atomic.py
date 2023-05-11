import os
import shutil
import tempfile
from contextlib import contextmanager
from typing import BinaryIO, ContextManager, Literal, TextIO, overload

from filelock import FileLock

OpenTextMode = Literal["r+","+r","rt+","r+t","+rt","tr+","t+r","+tr","w+","+w","wt+","w+t","+wt","tw+","t+w","+tw","a+","+a","at+","a+t","+at","ta+","t+a","+ta","x+","+x","xt+","x+t","+xt","tx+","t+x","+tx","w","wt","tw","a","at","ta","x","xt","tx","r","rt","tr","U","rU","Ur","rtU","rUt","Urt","trU","tUr","Utr"] # pylint: disable=line-too-long  # fmt: skip
OpenBinaryMode = Literal["rb+","r+b","+rb","br+","b+r","+br","wb+","w+b","+wb","bw+","b+w","+bw","ab+","a+b","+ab","ba+","b+a","+ba","xb+","x+b","+xb","bx+","b+x","+bx","rb","br","rbU","rUb","Urb","brU","bUr","Ubr","wb","bw","ab","ba","xb","bx"] # pylint: disable=line-too-long  # fmt: skip


@overload
def atomic_write(
    path: str, mode: Literal[OpenTextMode] | None = "w", encoding: str | None = None
) -> ContextManager[TextIO]:
    ...


@overload
def atomic_write(
    path: str, mode: Literal[OpenBinaryMode], encoding: str | None = None
) -> ContextManager[BinaryIO]:
    ...


@contextmanager
def atomic_write(path, mode="w", encoding="utf-8"):
    with FileLock(f"{path}.lock"):
        # Open a temporary file in the same directory as the original file
        temp_file = tempfile.NamedTemporaryFile(
            mode, dir=os.path.dirname(path), delete=False, encoding=encoding
        )
        temp_path = temp_file.name

        # If the file already exists, copy its content to the temporary file
        if os.path.exists(path):
            with open(path, "r", encoding=encoding) as original_file:
                shutil.copyfileobj(original_file, temp_file)
            # move back to the beginning of the temp file so the user can read from the start
            temp_file.seek(0)

        try:
            yield temp_file  # This is the file that the user will interact with
        except:
            # If there was an exception, remove the temp file and re-raise the exception
            temp_file.close()
            os.remove(temp_path)
            raise
        else:
            # Ensure all buffered outputs are flushed to the disk
            temp_file.flush()
            os.fsync(temp_file.fileno())
            temp_file.close()

            # If there were no exceptions, replace the original file
            os.replace(temp_path, path)
