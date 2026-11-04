from itertools import count
from pathlib import Path

import pytest

from test.helpers.packages import INTERACTIVE_PACKAGE, NORMAL_PACKAGE, PackageFactory, prepare_package


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def package_factory(tmp_path: Path, fixtures_dir: Path) -> PackageFactory:
    sequence = count()

    def prepare(name: str, zipped: bool) -> Path:
        return prepare_package(fixtures_dir / name, tmp_path / f"package-{next(sequence)}", zipped=zipped)

    return prepare


@pytest.fixture
def polygon_dir(package_factory: PackageFactory) -> Path:
    return package_factory(NORMAL_PACKAGE, False)


@pytest.fixture
def interactive_dir(package_factory: PackageFactory) -> Path:
    return package_factory(INTERACTIVE_PACKAGE, False)
