import subprocess
import tempfile
from pathlib import Path
import glob
import os
from textwrap import dedent


def build_fake_package(
    package_name: str = "testpkg",
    version: str = "0.0.1",
    script_content: str = "echo 'Hello World!'",
) -> str:
    with tempfile.TemporaryDirectory() as pkg_dir:
        recipe_dir = Path(pkg_dir) / "recipe"
        recipe_dir.mkdir()

        meta_yaml_content = dedent(
            f"""
            package:
                name: {package_name}
                version: {version}

            build:
                number: 0
                script: {script_content} > $PREFIX/bin/{package_name}.sh

            requirements:
                build:
                    - python
                run:
                    - python

            about:
                license: MIT
                summary: "A test package for automated repository testing"
            """
        )

        # Write the temporary meta.yaml file
        (recipe_dir / "meta.yaml").write_text(meta_yaml_content)

        # Build the package
        subprocess.run(
            ["conda-build", str(recipe_dir)], check=True, capture_output=True
        )

        # The TemporaryDirectory context manager automatically cleans up the directory here

    # Search for the built packages
    conda_build_dir = os.path.join(os.environ["CONDA_PREFIX"], "conda-bld")
    matched_files = glob.glob(
        f"**/{package_name}-{version}-*", root_dir=conda_build_dir, recursive=True
    )

    # Raise an error if the package was not found
    assert (
        len(matched_files) > 0
    ), f"Package {package_name}-{version} not found in {conda_build_dir}"

    # Return the path to the built package
    return os.path.join(conda_build_dir, matched_files[0])
