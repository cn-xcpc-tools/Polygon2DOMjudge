import shutil
import zipfile
from os import chdir
from pathlib import Path

import pytest

from typer.testing import CliRunner

from .utils.dataloader import load_cli_test_data, load_api_test_data

runner = CliRunner()


@pytest.fixture(scope="function")
def temp_dir(tmp_path):
    old_cwd = Path.cwd()
    chdir(tmp_path)
    yield tmp_path
    chdir(old_cwd)


def test_import():
    from p2d import __main__  # noqa: F401


def test_version():
    from p2d._version import __version__

    assert len(__version__) > 0


def test_cli_version():
    from p2d._version import __version__
    from p2d.cli import app

    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


@pytest.mark.parametrize("extract", [True, False], ids=["dir", "zip"])
@pytest.mark.parametrize("package_name, args, assertion, expectation", load_api_test_data())
def test_api(temp_dir, package_name, extract, args, assertion, expectation):
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
        convert(package, domjudge_package, **args)

        assert domjudge_package.is_file()

        # Extract the output zip file for further assertion
        with zipfile.ZipFile(domjudge_package, "r") as zip_ref:
            zip_ref.extractall(domjudge_package_dir)

        assertion(domjudge_package_dir)


@pytest.mark.parametrize("extract", [True, False], ids=["dir", "zip"])
@pytest.mark.parametrize("package_name, args, user_input, assertion, exitcode", load_cli_test_data())
def test_cli(temp_dir, package_name, args, user_input, extract, assertion, exitcode):
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
