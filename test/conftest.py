"""Shared pytest fixtures for all tests."""

import shutil
import zipfile
from collections.abc import Callable, Generator
from os import chdir
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary directory and change to it for the test duration."""
    old_cwd = Path.cwd()
    chdir(tmp_path)
    yield tmp_path
    chdir(old_cwd)


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to the test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def prepare_package(
    temp_dir: Path,
    fixtures_dir: Path,
    request: pytest.FixtureRequest,
) -> Callable[[str], Path]:
    """Provide a function to prepare test packages (copy and optionally extract).

    The `extract` parameter is provided via indirect parametrization.
    Returns a function that takes a package name and returns the path to use.
    """
    extract: bool = getattr(request, "param", False)

    def _prepare(package_name: str) -> Path:
        polygon_package = temp_dir / "example-polygon.zip"

        src = fixtures_dir / package_name
        if src.exists():
            shutil.copyfile(src, polygon_package)
            if extract:
                polygon_dir = temp_dir / "example-polygon-dir"
                with zipfile.ZipFile(polygon_package, "r") as zip_ref:
                    zip_ref.extractall(polygon_dir)
                return polygon_dir

        return polygon_package

    return _prepare


@pytest.fixture
def domjudge_package_path(temp_dir: Path) -> Path:
    """Return the path for the output DOMjudge package."""
    return temp_dir / "example-domjudge.zip"


@pytest.fixture
def extract_domjudge_package(temp_dir: Path) -> Callable[[Path], Path]:
    """Provide a function to extract the DOMjudge package for assertion."""

    def _extract(package_path: Path) -> Path:
        output_dir = temp_dir / "example-domjudge-dir"
        with zipfile.ZipFile(package_path, "r") as zip_ref:
            zip_ref.extractall(output_dir)
        return output_dir

    return _extract
