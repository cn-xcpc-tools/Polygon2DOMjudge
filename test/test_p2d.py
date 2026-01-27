"""Tests for the Polygon2DOMjudge conversion functionality."""

from collections.abc import Callable
from pathlib import Path
from typing import Any, ContextManager

import pytest
from typer.testing import CliRunner

from p2d import GlobalConfig

from .helpers.dataloader import load_api_test_data, load_cli_test_data
from .helpers.models import ConvertConfig

runner = CliRunner()


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


@pytest.mark.parametrize("prepare_package", [True, False], ids=["dir", "zip"], indirect=True)
@pytest.mark.parametrize(("package_name", "global_config", "convert_config", "assertion", "expectation"), load_api_test_data())
def test_api(
    prepare_package: Callable[[str], Path],
    domjudge_package_path: Path,
    extract_domjudge_package: Callable[[Path], Path],
    package_name: str,
    global_config: GlobalConfig,
    convert_config: ConvertConfig,
    assertion: Callable[[Path], None],
    expectation: ContextManager[Any],
) -> None:
    from p2d import convert

    package = prepare_package(package_name)
    short_name, options = convert_config.build(global_config, domjudge_package_path)

    with expectation:
        # Skip confirmation for testing
        convert(package=package, short_name=short_name, options=options, confirm=lambda: True)

        assert domjudge_package_path.is_file()
        domjudge_dir = extract_domjudge_package(domjudge_package_path)
        assertion(domjudge_dir)


@pytest.mark.parametrize("prepare_package", [True, False], ids=["dir", "zip"], indirect=True)
@pytest.mark.parametrize(("package_name", "args", "user_input", "assertion", "exitcode"), load_cli_test_data())
def test_cli(
    prepare_package: Callable[[str], Path],
    domjudge_package_path: Path,
    extract_domjudge_package: Callable[[Path], Path],
    package_name: str,
    args: list[str],
    user_input: str | None,
    assertion: Callable[[Path], None],
    exitcode: int,
) -> None:
    from p2d.cli import app

    package = prepare_package(package_name)
    result = runner.invoke(app, [str(package), *args], input=user_input)

    assert result.exit_code == exitcode

    if exitcode == 0:
        assert domjudge_package_path.is_file()
        domjudge_dir = extract_domjudge_package(domjudge_package_path)
        assertion(domjudge_dir)
