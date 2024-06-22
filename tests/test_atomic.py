import glob
import os
import shutil
from pathlib import Path

from conda_server.atomic import atomic_write


def test_atomic_write(testpkg: Path):
    testpkg_dir, testpkg_filename = os.path.split(testpkg)
    with open(testpkg, "rb") as testpkg_file:
        test_output_path = f"{testpkg_dir}/test_output"
        copy_path = f"{test_output_path}/{testpkg_filename}.copy"
        with atomic_write(copy_path, mode="wb") as buffer:
            shutil.copyfileobj(testpkg_file, buffer)

    assert not glob.glob(f"{test_output_path}/*.tmp")
    assert not Path(f"{copy_path}.lock").exists()
    assert Path(copy_path).exists()
