import logging
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

import pytest
import yaml
from typer.testing import CliRunner

from p2d import DomjudgeOptions
from p2d.cli import app
from test.helpers.packages import (
    INTERACTIVE_PACKAGE,
    NORMAL_PACKAGE,
    PackageFactory,
    export,
    read_archive,
)

POLYGON_URL = "https://polygon.codeforces.com/p2e3I1Z/Dup4/little-h-reboot"
LEGACY_WARNING = "Legacy export is deprecated and may be removed at any time."


@pytest.mark.parametrize("via_cli", [False, True], ids=["api", "cli"])
@pytest.mark.parametrize("zipped", [False, True], ids=["directory", "zip"])
@pytest.mark.parametrize(
    ("legacy", "metadata", "validator", "wrong_submission"),
    [
        pytest.param(
            False,
            {
                "problem_format_version": "2025-09",
                "uuid": str(uuid5(NAMESPACE_URL, POLYGON_URL)),
                "name": "Little H And Reboot",
                "type": "pass-fail",
                "limits": {"time_limit": 5.0, "time_resolution": 0.001, "memory": 256},
            },
            "output_validator",
            "rejected",
            id="2025-09",
        ),
        pytest.param(
            True,
            {"name": "Little H And Reboot", "limits": {"memory": 256}, "validation": "custom"},
            "output_validators/checker",
            "mixed",
            id="legacy",
        ),
    ],
)
def test_conversion(
    cli_runner: CliRunner,
    package_factory: PackageFactory,
    polygon_dir: Path,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    via_cli: bool,
    zipped: bool,
    legacy: bool,
    metadata: dict[str, Any],
    validator: str,
    wrong_submission: str,
) -> None:
    caplog.set_level(logging.WARNING)
    package = package_factory(NORMAL_PACKAGE, zipped)
    output = tmp_path / "result.zip"
    if via_cli:
        args = [str(package), "--code", "A", "-o", str(output), "-y"]
        if legacy:
            args.append("--legacy")
        result = cli_runner.invoke(app, args)
        assert result.exit_code == 0, result.output
        files = read_archive(output)
    else:
        files = export(package, output, DomjudgeOptions(legacy=legacy))

    assert yaml.safe_load(files["problem.yaml"]) == metadata
    assert files["domjudge-problem.ini"] == (
        b"short-name = A\ntimelimit = 5.0\ncolor = #000000\nexternalid = little-h-reboot\n"
    )
    assert {name for name in files if name.startswith("output_validator")} == {
        f"{validator}/check.cpp",
        f"{validator}/testlib.h",
    }
    assert not any(name.endswith("test_group.yaml") for name in files)
    assert "problem_statement/problem.pdf" not in files
    assert not any(name.startswith("attachments/") for name in files)
    assert b"\r" not in files["problem.yaml"]
    assert "submissions/submissions.yaml" not in files
    assert "submissions/accepted/std.cpp" in files
    wrong_source = files[f"submissions/{wrong_submission}/wrong.cpp"]
    if legacy:
        assert b"@EXPECTED_RESULTS@: WRONG-ANSWER, TIMELIMIT, RUN-ERROR" in wrong_source
    else:
        assert files["submissions/accepted/std.cpp"] == (polygon_dir / "solutions/std.cpp").read_bytes()
        assert wrong_source == (polygon_dir / "solutions/wrong.cpp").read_bytes()
    assert files["data/sample/01.in"] == (polygon_dir / "tests/01").read_bytes()
    assert files["data/sample/01.ans"] == (polygon_dir / "statements/english/example.01.a").read_bytes()
    assert files["data/sample/01.desc"] == b'File "01"\n'
    assert "data/secret/02.in" in files
    assert "data/secret/02.ans" in files
    assert caplog.messages.count(LEGACY_WARNING) == int(legacy)


@pytest.mark.parametrize("via_cli", [False, True], ids=["api", "cli"])
@pytest.mark.parametrize("zipped", [False, True], ids=["directory", "zip"])
@pytest.mark.parametrize(
    ("legacy", "metadata", "validator"),
    [
        pytest.param(
            False,
            {
                "problem_format_version": "2025-09",
                "uuid": str(uuid5(NAMESPACE_URL, "https://polygon.codeforces.com/p2IByNB/2014CAIS01/guess-array")),
                "name": "Guess The Array",
                "type": "interactive",
                "limits": {"time_limit": 1.0, "time_resolution": 0.001, "memory": 512},
            },
            "output_validator",
            id="2025-09",
        ),
        pytest.param(
            True,
            {"name": "Guess The Array", "limits": {"memory": 512}, "validation": "custom interactive"},
            "output_validators/interactor",
            id="legacy",
        ),
    ],
)
def test_interactive_conversion(
    cli_runner: CliRunner,
    package_factory: PackageFactory,
    tmp_path: Path,
    via_cli: bool,
    zipped: bool,
    legacy: bool,
    metadata: dict[str, Any],
    validator: str,
) -> None:
    package = package_factory(INTERACTIVE_PACKAGE, zipped)
    output = tmp_path / "interactive.zip"
    if via_cli:
        args = [str(package), "--code", "A", "--color", "#FF0000", "--auto", "-o", str(output), "-y"]
        if legacy:
            args.append("--legacy")
        result = cli_runner.invoke(app, args)
        assert result.exit_code == 0, result.output
        files = read_archive(output)
    else:
        files = export(package, output, DomjudgeOptions(legacy=legacy, color="#FF0000", auto_detect_std_checker=True))

    assert yaml.safe_load(files["problem.yaml"]) == metadata
    assert files["domjudge-problem.ini"] == (b"short-name = A\ntimelimit = 1.0\ncolor = #FF0000\nexternalid = guess-array\n")
    assert f"{validator}/interactor.cpp" in files
    assert f"{validator}/testlib.h" in files
    assert "submissions/accepted/std.cpp" in files
    assert {"data/sample/01.in", "data/sample/01.ans", "data/secret/02.in", "data/secret/02.ans"} <= files.keys()
    assert "data/sample/01.desc" not in files
    assert files["data/secret/02.desc"] == b"[GEN] random_gen -n 10 1\n"
