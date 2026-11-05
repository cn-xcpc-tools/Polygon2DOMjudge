import os
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from p2d import DomjudgeOptions, ProblemType, ProcessError
from p2d.cli import app
from test.helpers.packages import export, read_archive


@pytest.fixture
def testlib_header() -> bytes:
    return (Path(__file__).resolve().parents[2] / "p2d/testlib/testlib.h").read_bytes()


@pytest.mark.parametrize("legacy", [False, True], ids=["2025-09", "legacy"])
@pytest.mark.parametrize(
    ("problem_types", "interactive", "multi_pass"),
    [
        (["pass-fail"], False, False),
        (["interactive"], True, False),
        (["multi-pass"], False, True),
        (["interactive", "multi-pass"], True, True),
        (["multi-pass", "interactive"], True, True),
        (["interactive", "multi-pass", "interactive"], True, True),
        (["pass-fail", "pass-fail"], False, False),
        (["pass-fail", "interactive"], True, False),
        (["multi-pass", "pass-fail"], False, True),
        (["interactive", "pass-fail", "multi-pass"], True, True),
    ],
)
@pytest.mark.parametrize("source_interactive", [False, True], ids=["ordinary-source", "multi-pass-source"])
def test_cli_type_and_validator_overrides(
    cli_runner: CliRunner,
    polygon_dir: Path,
    interactive_dir: Path,
    tmp_path: Path,
    legacy: bool,
    problem_types: list[str],
    interactive: bool,
    multi_pass: bool,
    source_interactive: bool,
    testlib_header: bytes,
) -> None:
    package = interactive_dir if source_interactive else polygon_dir
    tree = ET.parse(package / "problem.xml")
    judging = tree.find("judging")
    statements = tree.find("statements")
    assets = tree.find("assets")
    assert judging is not None and statements is not None and assets is not None
    judging.set("run-count", "3" if source_interactive else "1")
    statements.set("use-interaction-log-in-example-tests", "true")
    for element in assets.findall("checker"):
        assets.remove(element)
    interactor = assets.find("interactor/source")
    if interactor is not None:
        interactor.set("path", "missing-interactor.cpp")
    tree.write(package / "problem.xml", encoding="utf-8")
    (package / "statements/english/example.01.a").write_bytes(b"statement output\n")
    if interactive and not multi_pass:
        (package / "statements/english/example.01.i").write_bytes(b"< 1\n> 2\n")

    validator = tmp_path / "custom validator.cpp"
    validator.write_bytes(b"int main() { return 42; }\n")
    output = tmp_path / "override.zip"
    args = [
        str(package),
        "--code",
        "A",
        "-o",
        str(output),
        "-y",
        *[arg for problem_type in problem_types for arg in ("--type", problem_type)],
        "--output-validator",
        str(validator),
        "--validator-flags",
        "--mode domjudge",
    ]
    if legacy:
        args.append("--legacy")
    result = cli_runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    files = read_archive(output)
    metadata = yaml.safe_load(files["problem.yaml"])
    modifiers = [name for name, enabled in (("interactive", interactive), ("multi-pass", multi_pass)) if enabled]
    if legacy:
        assert metadata["validation"] == " ".join(["custom", *modifiers])
        assert metadata["validator_flags"] == "--mode domjudge"
        validator_prefix = "output_validators/interactor" if interactive or multi_pass else "output_validators/checker"
    else:
        assert metadata["type"] == (" ".join(modifiers) if modifiers else "pass-fail")
        assert "validation" not in metadata
        validator_prefix = "output_validator"
        for group in ("sample", "secret"):
            assert yaml.safe_load(files[f"data/{group}/test_group.yaml"]) == {"output_validator_args": "--mode domjudge"}
    if multi_pass:
        assert metadata["limits"]["validation_passes"] == (3 if source_interactive else 2)
    else:
        assert "validation_passes" not in metadata["limits"]
    assert {name: content for name, content in files.items() if name.startswith("output_validator")} == {
        f"{validator_prefix}/{validator.name}": validator.read_bytes(),
        f"{validator_prefix}/testlib.h": testlib_header,
    }
    if multi_pass:
        assert files["data/secret/01.in"] == (package / "tests/01").read_bytes()
        assert files["data/secret/01.ans"] == (package / "tests/01.a").read_bytes()
        assert "data/sample/01.in" not in files
        assert "data/sample/01.ans" not in files
        assert not any(name.endswith(".interaction") for name in files)
    elif interactive:
        assert files["data/sample/01.ans"] == (package / "tests/01.a").read_bytes()
        assert files["data/sample/01.interaction"] == b"< 1\n> 2\n"
    else:
        assert files["data/sample/01.ans"] == b"statement output\n"
        assert not any(name.endswith(".interaction") for name in files)


@pytest.mark.parametrize("legacy", [False, True], ids=["2025-09", "legacy"])
@pytest.mark.parametrize("filename", ["validator.cpp", "run"])
def test_single_validator_file(polygon_dir: Path, tmp_path: Path, legacy: bool, filename: str, testlib_header: bytes) -> None:
    validator = tmp_path / filename
    validator.write_bytes(b"custom validator\r\n")
    validator.chmod(0o755)
    output = tmp_path / "single.zip"
    files = export(polygon_dir, output, DomjudgeOptions(legacy=legacy, output_validator=validator))
    prefix = "output_validators/checker" if legacy else "output_validator"
    expected = {f"{prefix}/{filename}": validator.read_bytes()}
    if filename.endswith(".cpp"):
        expected[f"{prefix}/testlib.h"] = testlib_header
    assert {name: content for name, content in files.items() if name.startswith("output_validator")} == expected
    with zipfile.ZipFile(output) as archive:
        assert (archive.getinfo(f"{prefix}/{filename}").external_attr >> 16) & 0o777 == 0o755


@pytest.mark.parametrize(
    ("args", "expected_type", "passes", "role"),
    [
        (["--type", "pass-fail"], "pass-fail", None, "checker.py"),
        (["--type", "interactive", "--type", "multi-pass"], "interactive multi-pass", 2, "interactor.cpp"),
        (["--type", "multi-pass"], "multi-pass", 2, "interactor.cpp"),
        (["--type", "interactive"], "interactive", None, "interactor.cpp"),
    ],
)
def test_type_override_with_polygon_validator(
    cli_runner: CliRunner,
    interactive_dir: Path,
    tmp_path: Path,
    args: list[str],
    expected_type: str,
    passes: int | None,
    role: str,
) -> None:
    tree = ET.parse(interactive_dir / "problem.xml")
    judging = tree.find("judging")
    assert judging is not None
    judging.set("run-count", "2")
    tree.write(interactive_dir / "problem.xml", encoding="utf-8")
    output = tmp_path / "type.zip"
    result = cli_runner.invoke(app, [str(interactive_dir), "--code", "A", "-o", str(output), "-y", *args])
    assert result.exit_code == 0, result.output
    files = read_archive(output)
    metadata = yaml.safe_load(files["problem.yaml"])
    assert metadata["type"] == expected_type
    assert metadata["limits"].get("validation_passes") == passes
    assert f"output_validator/{role}" in files
    assert ("output_validator/build" in files) == (passes is not None)


def test_override_validation_passes(cli_runner: CliRunner, polygon_dir: Path, tmp_path: Path) -> None:
    validator = tmp_path / "validator.cpp"
    validator.write_text("int main() { return 42; }\n", encoding="utf-8")
    output = tmp_path / "passes.zip"
    result = cli_runner.invoke(
        app,
        [
            str(polygon_dir),
            "--code",
            "A",
            "-o",
            str(output),
            "-y",
            "--type",
            "multi-pass",
            "--validation-passes",
            "5",
            "--output-validator",
            str(validator),
        ],
    )
    assert result.exit_code == 0, result.output
    metadata = yaml.safe_load(read_archive(output)["problem.yaml"])
    assert metadata["type"] == "multi-pass"
    assert metadata["limits"]["validation_passes"] == 5


@pytest.mark.parametrize("flag", ["--auto", "--default"])
def test_cli_conflicting_validator_override(cli_runner: CliRunner, polygon_dir: Path, tmp_path: Path, flag: str) -> None:
    validator = tmp_path / "validator.cpp"
    validator.write_text("int main() {}\n", encoding="utf-8")
    output = tmp_path / "conflict.zip"
    result = cli_runner.invoke(
        app,
        [
            str(polygon_dir),
            "--code",
            "A",
            "-o",
            str(output),
            "-y",
            flag,
            "--output-validator",
            str(validator),
        ],
    )
    assert result.exit_code == 2, result.output
    assert "Cannot use --output-validator with --default or --auto." in result.stderr
    assert not output.exists()


@pytest.mark.parametrize(
    ("options", "exception", "message"),
    [
        (DomjudgeOptions(problem_types=frozenset({ProblemType.INTERACTIVE})), ProcessError, "No interactor found"),
        (
            DomjudgeOptions(problem_types=frozenset({ProblemType.MULTI_PASS})),
            ProcessError,
            "requires a Polygon interactor or --output-validator",
        ),
        (DomjudgeOptions(validation_passes=3), ValueError, "requires a multi-pass problem"),
        (
            DomjudgeOptions(force_default_validator=True, problem_types=frozenset({ProblemType.INTERACTIVE})),
            ValueError,
            "require a custom output validator",
        ),
        (
            DomjudgeOptions(force_default_validator=True, problem_types=frozenset({ProblemType.MULTI_PASS})),
            ValueError,
            "require a custom output validator",
        ),
    ],
)
def test_invalid_overrides(
    polygon_dir: Path, tmp_path: Path, options: DomjudgeOptions, exception: type[Exception], message: str
) -> None:
    output = tmp_path / "invalid.zip"
    with pytest.raises(exception, match=message):
        export(polygon_dir, output, options)
    assert not output.exists()


@pytest.mark.parametrize("auto", [False, True])
def test_api_conflicting_validator_override(polygon_dir: Path, tmp_path: Path, auto: bool) -> None:
    with pytest.raises(ValueError, match="Cannot use --output-validator with --default or --auto"):
        export(
            polygon_dir,
            tmp_path / "invalid.zip",
            DomjudgeOptions(
                output_validator=tmp_path / "validator.cpp",
                auto_detect_std_checker=auto,
                force_default_validator=not auto,
            ),
        )


def test_missing_validator_override(polygon_dir: Path, tmp_path: Path) -> None:
    missing = tmp_path / "missing.cpp"
    with pytest.raises(FileNotFoundError) as exc:
        export(polygon_dir, tmp_path / "missing.zip", DomjudgeOptions(output_validator=missing))
    assert Path(exc.value.filename) == missing


@pytest.mark.parametrize(
    ("passes", "interactive_runs", "expected_type"),
    [(1, False, "interactive"), (2, False, "multi-pass"), (2, True, "interactive multi-pass")],
)
def test_validator_override_preserves_inferred_type(
    interactive_dir: Path, tmp_path: Path, passes: int, interactive_runs: bool, expected_type: str
) -> None:
    tree = ET.parse(interactive_dir / "problem.xml")
    judging = tree.find("judging")
    interactor = tree.find("assets/interactor")
    assert judging is not None and interactor is not None
    judging.set("run-count", str(passes))
    if interactive_runs:
        runs = ET.SubElement(interactor, "runs")
        ET.SubElement(runs, "run")
        ET.SubElement(runs, "run")
    tree.write(interactive_dir / "problem.xml", encoding="utf-8")
    validator = tmp_path / "validator.cpp"
    validator.write_text("int main() { return 42; }\n", encoding="utf-8")
    files = export(interactive_dir, tmp_path / "inferred.zip", DomjudgeOptions(output_validator=validator))
    metadata = yaml.safe_load(files["problem.yaml"])
    assert metadata["type"] == expected_type
    assert metadata["limits"].get("validation_passes") == (passes if passes > 1 else None)
    assert {name for name in files if name.startswith("output_validator")} == {
        "output_validator/validator.cpp",
        "output_validator/testlib.h",
    }


@pytest.mark.parametrize("default", [False, True], ids=["auto", "default"])
@pytest.mark.parametrize("problem_types", [frozenset(), frozenset({ProblemType.PASS_FAIL})], ids=["implicit", "explicit"])
def test_default_validator_after_type_override(
    interactive_dir: Path, tmp_path: Path, default: bool, problem_types: frozenset[ProblemType]
) -> None:
    tree = ET.parse(interactive_dir / "problem.xml")
    judging = tree.find("judging")
    checker = tree.find("assets/checker")
    assert judging is not None and checker is not None
    judging.set("run-count", "3")
    checker.set("name", "std::wcmp.cpp")
    tree.write(interactive_dir / "problem.xml", encoding="utf-8")
    files = export(
        interactive_dir,
        tmp_path / "default.zip",
        DomjudgeOptions(
            problem_types=problem_types,
            force_default_validator=default,
            auto_detect_std_checker=not default,
        ),
    )
    metadata = yaml.safe_load(files["problem.yaml"])
    assert metadata["type"] == "pass-fail"
    assert "validation_passes" not in metadata["limits"]
    assert not any(name.startswith("output_validator") for name in files)


@pytest.mark.parametrize(
    "args",
    [
        ["--output-validator", "missing.cpp"],
        ["--output-validator", "."],
        ["--validation-passes", "1"],
        ["--type", "unknown"],
        ["--type"],
    ],
)
def test_invalid_cli_override_arguments(cli_runner: CliRunner, polygon_dir: Path, tmp_path: Path, args: list[str]) -> None:
    output = tmp_path / "invalid.zip"
    result = cli_runner.invoke(app, [str(polygon_dir), "--code", "A", "-o", str(output), "-y", *args])
    assert result.exit_code == 2, result.output
    assert not output.exists()


def test_validator_override_requires_file(polygon_dir: Path, tmp_path: Path) -> None:
    output = tmp_path / "invalid.zip"
    with pytest.raises(ValueError, match="--output-validator must be a regular file"):
        export(polygon_dir, output, DomjudgeOptions(output_validator=tmp_path))
    assert not output.exists()


def test_polygon_interactor_pass_limit(interactive_dir: Path, tmp_path: Path) -> None:
    tree = ET.parse(interactive_dir / "problem.xml")
    judging = tree.find("judging")
    assert judging is not None
    judging.set("run-count", "3")
    tree.write(interactive_dir / "problem.xml", encoding="utf-8")
    with pytest.raises(ProcessError, match="supports only 2 passes; supply --output-validator for more passes"):
        export(interactive_dir, tmp_path / "invalid.zip")


@pytest.mark.parametrize(
    ("problem_types", "expected_type"),
    [
        (["pass-fail"], "pass-fail"),
        (["interactive"], "interactive"),
        (["multi-pass"], "multi-pass"),
        (["interactive", "multi-pass"], "interactive multi-pass"),
        (["pass-fail", "interactive"], "interactive"),
        (["multi-pass", "pass-fail"], "multi-pass"),
        (["pass-fail", "interactive", "multi-pass"], "interactive multi-pass"),
        ([], "pass-fail"),
    ],
)
def test_api_problem_type_override(polygon_dir: Path, tmp_path: Path, problem_types: list[str], expected_type: str) -> None:
    validator = tmp_path / "validator.cpp"
    validator.write_text("int main() { return 42; }\n", encoding="utf-8")
    options = DomjudgeOptions.model_validate({"problem_types": problem_types, "output_validator": validator})
    files = export(polygon_dir, tmp_path / "typed.zip", options)
    metadata = yaml.safe_load(files["problem.yaml"])
    assert metadata["type"] == expected_type
    assert metadata["limits"].get("validation_passes") == (2 if "multi-pass" in expected_type else None)
    assert files["output_validator/validator.cpp"] == validator.read_bytes()


@pytest.mark.parametrize("legacy", [False, True], ids=["2025-09", "legacy"])
def test_validator_under_files_with_custom_testlib(polygon_dir: Path, tmp_path: Path, legacy: bool) -> None:
    validator = polygon_dir / "files/domjudge-validator.cpp"
    validator.write_text('#include "testlib.h"\nint main() { return 42; }\n', encoding="utf-8")
    header_dir = tmp_path / "custom-testlib"
    header_dir.mkdir()
    header = header_dir / "testlib.h"
    header.write_bytes(b"#define CUSTOM_TESTLIB 1\n")
    output = tmp_path / "custom.zip"
    args = [
        sys.executable,
        "-m",
        "p2d",
        ".",
        "--code",
        "A",
        "-o",
        str(output),
        "-y",
        "--type",
        "multi-pass",
        "--output-validator",
        "files/domjudge-validator.cpp",
    ]
    if legacy:
        args.append("--legacy")
    result = subprocess.run(
        args,
        cwd=polygon_dir,
        env={**os.environ, "TESTLIB_PATH": str(header_dir)},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    assert result.returncode == 0, result.stdout
    files = read_archive(output)
    prefix = "output_validators/interactor" if legacy else "output_validator"
    assert {name: content for name, content in files.items() if name.startswith("output_validator")} == {
        f"{prefix}/domjudge-validator.cpp": validator.read_bytes(),
        f"{prefix}/testlib.h": header.read_bytes(),
    }


@pytest.mark.parametrize("legacy", [False, True], ids=["2025-09", "legacy"])
@pytest.mark.parametrize("explicit_type", [False, True], ids=["inferred", "overridden"])
@pytest.mark.parametrize("hide_sample", [None, False, True], ids=["default", "visible", "hidden"])
def test_cli_multi_pass_sample_visibility(
    cli_runner: CliRunner,
    interactive_dir: Path,
    tmp_path: Path,
    legacy: bool,
    explicit_type: bool,
    hide_sample: bool | None,
) -> None:
    tree = ET.parse(interactive_dir / "problem.xml")
    judging = tree.find("judging")
    statements = tree.find("statements")
    assert judging is not None and statements is not None
    judging.set("run-count", "1" if explicit_type else "2")
    statements.set("use-interaction-log-in-example-tests", "true")
    tree.write(interactive_dir / "problem.xml", encoding="utf-8")
    interaction = b"< 1\n> 2\n"
    if hide_sample is False:
        (interactive_dir / "statements/english/example.01.i").write_bytes(interaction)
    output = tmp_path / "samples.zip"
    args = [str(interactive_dir), "--code", "A", "-o", str(output), "-y", "--keep", "1"]
    if legacy:
        args.append("--legacy")
    if explicit_type:
        args.extend(["--type", "interactive", "--type", "multi-pass"])
    if hide_sample is not None:
        args.append("--hide-sample" if hide_sample else "--no-hide-sample")
    result = cli_runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    files = read_archive(output)
    hidden = hide_sample is not False
    group = "secret" if hidden else "sample"
    assert files[f"data/{group}/01.in"] == (interactive_dir / "tests/01").read_bytes()
    assert files[f"data/{group}/01.ans"] == (interactive_dir / "tests/01.a").read_bytes()
    if hidden:
        assert not any(name.startswith("data/sample/") or name.endswith(".interaction") for name in files)
    else:
        assert files["data/sample/01.interaction"] == interaction
        assert "data/secret/01.in" not in files
