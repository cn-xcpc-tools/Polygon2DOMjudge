import shutil
import zipfile
from collections.abc import Callable, Generator
from os import chdir
from pathlib import Path
from typing import Any, ContextManager

import pytest
from typer.testing import CliRunner

from p2d import GlobalConfig
from p2d.p2d import ConvertOptions

from .utils.dataloader import load_api_test_data, load_cli_test_data

runner = CliRunner()


@pytest.fixture
def temp_dir(tmp_path: Path) -> Generator[Path, None, None]:
    old_cwd = Path.cwd()
    chdir(tmp_path)
    yield tmp_path
    chdir(old_cwd)


def test_import() -> None:
    from p2d import __main__  # noqa: F401


def test_version() -> None:
    from p2d._version import __version__

    assert len(__version__) > 0


def test_cli_version() -> None:
    from p2d._version import __version__
    from p2d.cli import app

    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


@pytest.mark.parametrize("extract", [True, False], ids=["dir", "zip"])
@pytest.mark.parametrize(("package_name", "global_config", "kwargs", "assertion", "expectation"), load_api_test_data())
def test_api(
    temp_dir: Path,
    package_name: str,
    extract: bool,
    global_config: GlobalConfig,
    kwargs: ConvertOptions,
    assertion: Callable[[Path], None],
    expectation: ContextManager[Any],
) -> None:
    test_data_dir = Path(__file__).parent / "test_data"
    polygon_package_dir = temp_dir / "example-polygon-dir"
    domjudge_package_dir = temp_dir / "example-domjudge-dir"
    polygon_package = temp_dir / "example-polygon.zip"
    domjudge_package = temp_dir / "example-domjudge.zip"

    if (test_data_dir / package_name).exists():
        # there are some test cases that tests the package is not found
        # keep this error in api calling.
        shutil.copyfile(test_data_dir / package_name, polygon_package)
        if extract:
            with zipfile.ZipFile(polygon_package, "r") as zip_ref:
                zip_ref.extractall(polygon_package_dir)

    from p2d import convert

    package = polygon_package_dir if extract else polygon_package

    with expectation:
        # Skip confirmation for testing
        convert(package, domjudge_package, global_config=global_config, **kwargs)

        assert domjudge_package.is_file()

        # Extract the output zip file for further assertion
        with zipfile.ZipFile(domjudge_package, "r") as zip_ref:
            zip_ref.extractall(domjudge_package_dir)

        assertion(domjudge_package_dir)


@pytest.mark.parametrize("extract", [True, False], ids=["dir", "zip"])
@pytest.mark.parametrize(("package_name", "args", "user_input", "assertion", "exitcode"), load_cli_test_data())
def test_cli(
    temp_dir: Path,
    package_name: str,
    args: list[str],
    user_input: str | None,
    extract: bool,
    assertion: Callable[[Path], None],
    exitcode: int,
) -> None:
    test_data_dir = Path(__file__).parent / "test_data"
    polygon_package_dir = temp_dir / "example-polygon-dir"
    domjudge_package_dir = temp_dir / "example-domjudge-dir"
    polygon_package = temp_dir / "example-polygon.zip"
    domjudge_package = temp_dir / "example-domjudge.zip"

    if (test_data_dir / package_name).exists():
        # there are some test cases that tests the package is not found
        # keep this error in cli calling.
        shutil.copyfile(test_data_dir / package_name, polygon_package)
        if extract:
            with zipfile.ZipFile(polygon_package, "r") as zip_ref:
                zip_ref.extractall(polygon_package_dir)

    from p2d.cli import app

    package = polygon_package_dir if extract else polygon_package

    result = runner.invoke(app, [str(package), *args], input=user_input)

    assert result.exit_code == exitcode

    if exitcode == 0:
        assert domjudge_package.is_file()

        # Extract the output zip file for further assertion
        with zipfile.ZipFile(domjudge_package, "r") as zip_ref:
            zip_ref.extractall(domjudge_package_dir)

        assertion(domjudge_package_dir)
