import errno
from pathlib import Path

import pytest

from p2d import ConvertOptions, DomjudgeOptions, ProcessError, convert
from test.helpers.packages import NORMAL_PACKAGE, PackageFactory, export


def test_nested_output_directory(polygon_dir: Path, tmp_path: Path) -> None:
    files = export(polygon_dir, tmp_path / "nested" / "output" / "problem.zip")
    assert "problem.yaml" in files


@pytest.mark.parametrize("zipped", [False, True], ids=["directory", "zip"])
def test_missing_package(tmp_path: Path, zipped: bool) -> None:
    package = tmp_path / ("missing.zip" if zipped else "missing")
    output = tmp_path / "result.zip"
    with pytest.raises(FileNotFoundError) as exc:
        convert(package, short_name="A", options=ConvertOptions(output=output))
    assert exc.value.errno == errno.ENOENT
    assert exc.value.filename == package.name
    assert not output.exists()


@pytest.mark.parametrize("zipped", [False, True], ids=["directory", "zip"])
def test_missing_testset(package_factory: PackageFactory, tmp_path: Path, zipped: bool) -> None:
    package = package_factory(NORMAL_PACKAGE, zipped)
    output = tmp_path / "result.zip"
    with pytest.raises(ProcessError, match=r"^Can not find testset not-exist in problem\.xml\.$"):
        convert(package, short_name="A", options=ConvertOptions(output=output, testset_name="not-exist"))
    assert not output.exists()


def test_conflicting_validator_options(polygon_dir: Path, tmp_path: Path) -> None:
    output = tmp_path / "result.zip"
    options = DomjudgeOptions(auto_detect_std_checker=True, force_default_validator=True)
    with pytest.raises(
        ValueError, match=r"^Can not use auto_detect_std_checker and force_default_validator at the same time\.$"
    ):
        convert(polygon_dir, short_name="A", options=ConvertOptions(output=output, options=options))
    assert not output.exists()


def test_existing_output_is_preserved(polygon_dir: Path, tmp_path: Path) -> None:
    output = tmp_path / "result.zip"
    output.write_bytes(b"existing archive")
    with pytest.raises(FileExistsError) as exc:
        convert(polygon_dir, short_name="A", options=ConvertOptions(output=output))
    assert exc.value.errno == errno.EEXIST
    assert Path(exc.value.filename) == output
    assert output.read_bytes() == b"existing archive"


def test_declined_confirmation(polygon_dir: Path, tmp_path: Path) -> None:
    output = tmp_path / "result.zip"
    convert(polygon_dir, short_name="A", options=ConvertOptions(output=output), confirm=lambda: False)
    assert not output.exists()
