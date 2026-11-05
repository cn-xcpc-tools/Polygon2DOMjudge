import errno
from pathlib import Path

import pytest
import typer
import yaml
from rich.text import Text
from typer.testing import CliRunner

from p2d import ProcessError
from p2d._version import __version__
from p2d.cli import app
from p2d.contest import app as contest_app
from test.helpers.packages import NORMAL_PACKAGE, PackageFactory, read_archive


@pytest.mark.parametrize("legacy", [False, True], ids=["2025-09", "legacy"])
def test_tag_rules_from_toml(cli_runner: CliRunner, polygon_dir: Path, tmp_path: Path, legacy: bool) -> None:
    config = tmp_path / "rules.toml"
    config.write_text('[tag]\nmain = { permitted = ["AC"] }\nrejected = { permitted = ["AC", "TLE"] }\n', encoding="utf-8")
    output = tmp_path / "configured.zip"
    args = [str(polygon_dir), "--code", "A", "-o", str(output), "--config", str(config), "-y"]
    if legacy:
        args.append("--legacy")
    result = cli_runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    files = read_archive(output)
    if legacy:
        assert "submissions/submissions.yaml" not in files
        assert b"@EXPECTED_RESULTS@: CORRECT, TIMELIMIT" in files["submissions/mixed/wrong.cpp"]
    else:
        assert yaml.safe_load(files["submissions/submissions.yaml"]) == {"mixed/wrong.cpp": {"permitted": ["AC", "TLE"]}}


@pytest.mark.parametrize("application", [app, contest_app], ids=["problem", "contest"])
def test_version(cli_runner: CliRunner, application: typer.Typer) -> None:
    result = cli_runner.invoke(application, ["--version"])
    assert result.exit_code == 0, result.output
    assert result.stdout.strip() == f"Polygon Package to Domjudge Package v{__version__}"


def test_help(cli_runner: CliRunner) -> None:
    result = cli_runner.invoke(app, ["--help"])
    assert result.exit_code == 0, result.output
    assert "Process Polygon Package to Domjudge Package" in result.stdout


@pytest.mark.parametrize("legacy", [False, True], ids=["2025-09", "legacy"])
@pytest.mark.parametrize(
    ("args", "user_input"),
    [
        pytest.param([], "y\n", id="accept"),
        pytest.param(["--testset", "tests"], "\n", id="default-accept-explicit-testset"),
    ],
)
def test_confirmation(
    cli_runner: CliRunner, polygon_dir: Path, tmp_path: Path, legacy: bool, args: list[str], user_input: str
) -> None:
    output = tmp_path / "confirmed.zip"
    command = [str(polygon_dir), "--code", "A", "-o", str(output), *args]
    if legacy:
        command.append("--legacy")
    result = cli_runner.invoke(app, command, input=user_input)
    assert result.exit_code == 0, result.output
    assert "Are you sure to convert the package?" in result.stderr
    assert "problem.yaml" in read_archive(output)


def test_declined_confirmation(cli_runner: CliRunner, polygon_dir: Path, tmp_path: Path) -> None:
    output = tmp_path / "declined.zip"
    result = cli_runner.invoke(app, [str(polygon_dir), "--code", "A", "-o", str(output)], input="n\n")
    assert result.exit_code == 1, result.output
    assert "Are you sure to convert the package?" in result.stderr
    assert "Aborted" in result.stderr
    assert not output.exists()


def test_skip_confirmation(cli_runner: CliRunner, polygon_dir: Path, tmp_path: Path) -> None:
    output = tmp_path / "confirmed.zip"
    result = cli_runner.invoke(app, [str(polygon_dir), "--code", "A", "-o", str(output), "--yes"])
    assert result.exit_code == 0, result.output
    assert "Are you sure to convert the package?" not in result.output
    assert "problem.yaml" in read_archive(output)


@pytest.mark.parametrize("level", ["debug", "info", "warning", "error", "critical"])
def test_log_levels(cli_runner: CliRunner, polygon_dir: Path, tmp_path: Path, level: str) -> None:
    output = tmp_path / "logged.zip"
    result = cli_runner.invoke(app, [str(polygon_dir), "--code", "A", "-o", str(output), "--log-level", level, "-y"])
    assert result.exit_code == 0, result.output
    assert "problem.yaml" in read_archive(output)


@pytest.mark.parametrize("legacy", [False, True], ids=["2025-09", "legacy"])
@pytest.mark.parametrize(
    ("args", "flags"),
    [
        pytest.param(["--auto"], "float_tolerance 1e-4", id="auto"),
        pytest.param(["--default", "--validator-flags", "float_tolerance 1e-6"], "float_tolerance 1e-6", id="explicit"),
    ],
)
def test_validator_options(
    cli_runner: CliRunner, polygon_dir: Path, tmp_path: Path, legacy: bool, args: list[str], flags: str
) -> None:
    output = tmp_path / "validator.zip"
    command = [str(polygon_dir), "--code", "A", "-o", str(output), "-y", *args]
    if legacy:
        command.append("--legacy")
    result = cli_runner.invoke(app, command)
    assert result.exit_code == 0, result.output
    files = read_archive(output)
    metadata = yaml.safe_load(files["problem.yaml"])
    assert not any(name.startswith("output_validator") for name in files)
    if legacy:
        assert metadata["validation"] == "default"
        assert metadata["validator_flags"] == flags
        assert not any(name.endswith("test_group.yaml") for name in files)
    else:
        assert "validator_flags" not in metadata
        for group in ("sample", "secret"):
            assert yaml.safe_load(files[f"data/{group}/test_group.yaml"]) == {"output_validator_args": flags}
    assert {"data/sample/01.in", "data/sample/01.ans", "data/secret/02.in", "data/secret/02.ans"} <= files.keys()
    assert "submissions/accepted/std.cpp" in files


@pytest.mark.parametrize("legacy", [False, True], ids=["2025-09", "legacy"])
def test_hide_samples(cli_runner: CliRunner, polygon_dir: Path, tmp_path: Path, legacy: bool) -> None:
    output = tmp_path / "hidden.zip"
    args = [str(polygon_dir), "--code", "A", "-o", str(output), "--hide-sample", "-y"]
    if legacy:
        args.append("--legacy")
    result = cli_runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    files = read_archive(output)
    assert not any(name.startswith("data/sample/") for name in files)
    assert files["data/secret/01.in"] == (polygon_dir / "tests/01").read_bytes()
    assert files["data/secret/01.ans"] == (polygon_dir / "tests/01.a").read_bytes()
    assert {"data/secret/02.in", "data/secret/02.ans", "submissions/accepted/std.cpp"} <= files.keys()
    validator = "output_validators/checker" if legacy else "output_validator"
    assert {f"{validator}/check.cpp", f"{validator}/testlib.h"} <= files.keys()


@pytest.mark.parametrize(
    ("legacy", "limits"),
    [
        pytest.param(False, {"time_limit": 5.0, "time_resolution": 0.001, "output": 64}, id="2025-09"),
        pytest.param(True, {"output": 64}, id="legacy"),
    ],
)
def test_limit_overrides(
    cli_runner: CliRunner, polygon_dir: Path, tmp_path: Path, legacy: bool, limits: dict[str, int | float]
) -> None:
    output = tmp_path / "limits.zip"
    args = [
        str(polygon_dir),
        "--code",
        "A",
        "--color",
        "#FF0000",
        "-o",
        str(output),
        "--memory-limit",
        "-1",
        "--output-limit",
        "64",
        "-y",
    ]
    if legacy:
        args.append("--legacy")
    result = cli_runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    files = read_archive(output)
    assert yaml.safe_load(files["problem.yaml"])["limits"] == limits
    assert files["domjudge-problem.ini"] == (
        b"short-name = A\ntimelimit = 5.0\ncolor = #FF0000\nexternalid = little-h-reboot\n"
    )


@pytest.mark.parametrize(
    ("args", "message"),
    [
        pytest.param(["--default", "--auto"], 'Cannot use "--default" and "--auto" at the same time.', id="conflict"),
        pytest.param(["--color"], "requires an argument", id="missing-color"),
    ],
)
def test_invalid_options(cli_runner: CliRunner, polygon_dir: Path, tmp_path: Path, args: list[str], message: str) -> None:
    output = tmp_path / "invalid.zip"
    result = cli_runner.invoke(app, [str(polygon_dir), "--code", "A", "-o", str(output), "-y", *args])
    assert result.exit_code == 2, result.output
    assert message in Text.from_ansi(result.stderr).plain
    assert not output.exists()


def test_missing_package(cli_runner: CliRunner, tmp_path: Path) -> None:
    package = tmp_path / "missing.zip"
    output = tmp_path / "result.zip"
    result = cli_runner.invoke(app, [str(package), "--code", "A", "-o", str(output), "-y"])
    assert result.exit_code == 1, result.output
    assert isinstance(result.exception, FileNotFoundError)
    assert result.exception.errno == errno.ENOENT
    assert result.exception.filename == package.name
    assert not output.exists()


def test_missing_testset(cli_runner: CliRunner, polygon_dir: Path, tmp_path: Path) -> None:
    output = tmp_path / "result.zip"
    result = cli_runner.invoke(app, [str(polygon_dir), "--code", "A", "--testset", "not-exist", "-o", str(output), "-y"])
    assert result.exit_code == 1, result.output
    assert isinstance(result.exception, ProcessError)
    assert str(result.exception) == "Can not find testset not-exist in problem.xml."
    assert not output.exists()


def test_input_archive_cannot_be_overwritten(cli_runner: CliRunner, package_factory: PackageFactory) -> None:
    package = package_factory(NORMAL_PACKAGE, True)
    original = package.read_bytes()
    result = cli_runner.invoke(app, [str(package), "--code", "A", "-o", str(package), "-y"])
    assert result.exit_code == 1, result.output
    assert isinstance(result.exception, FileExistsError)
    assert result.exception.errno == errno.EEXIST
    assert result.exception.filename == str(package)
    assert package.read_bytes() == original
