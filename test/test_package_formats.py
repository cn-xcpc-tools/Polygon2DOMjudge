import logging
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import pytest
import yaml
from typer.testing import CliRunner

from p2d import ConvertOptions, DomjudgeOptions, GlobalConfig, ProcessError, SubmissionRule, convert
from p2d.cli import app

NORMAL_PACKAGE = "little-h-reboot-7$linux.zip"
POLYGON_URL = "https://polygon.codeforces.com/p2e3I1Z/Dup4/little-h-reboot"
LEGACY_WARNING = "Legacy export is deprecated and may be removed at any time."


@pytest.fixture
def polygon_dir(tmp_path: Path, fixtures_dir: Path) -> Path:
    directory = tmp_path / "polygon"
    with zipfile.ZipFile(fixtures_dir / NORMAL_PACKAGE) as archive:
        archive.extractall(directory)
    return directory


def read_archive(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        return {name: archive.read(name) for name in archive.namelist() if not name.endswith("/")}


def export(
    package: Path,
    output: Path,
    options: DomjudgeOptions = DomjudgeOptions(),
    config: GlobalConfig = GlobalConfig(),
    short_name: str = "A",
) -> dict[str, bytes]:
    convert(
        package,
        short_name=short_name,
        options=ConvertOptions(output=output, options=options, global_config=config),
        confirm=lambda: True,
    )
    return read_archive(output)


@pytest.mark.parametrize("via_cli", [False, True], ids=["api", "cli"])
@pytest.mark.parametrize("zipped", [False, True], ids=["directory", "zip"])
def test_default_export(
    polygon_dir: Path,
    fixtures_dir: Path,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    via_cli: bool,
    zipped: bool,
) -> None:
    package = fixtures_dir / NORMAL_PACKAGE if zipped else polygon_dir
    output = tmp_path / "result.zip"
    if via_cli:
        result = CliRunner().invoke(app, [str(package), "--code", "A", "-o", str(output), "-y"])
        assert result.exit_code == 0, result.output
        files = read_archive(output)
    else:
        files = export(package, output)

    assert yaml.safe_load(files["problem.yaml"]) == {
        "problem_format_version": "2025-09",
        "uuid": str(uuid5(NAMESPACE_URL, POLYGON_URL)),
        "name": "Little H And Reboot",
        "type": "pass-fail",
        "limits": {"time_limit": 5.0, "time_resolution": 0.001, "memory": 256},
    }
    assert files["domjudge-problem.ini"] == (
        b"short-name = A\ntimelimit = 5.0\ncolor = #000000\nexternalid = little-h-reboot\n"
    )
    assert "output_validator/check.cpp" in files
    assert "output_validator/testlib.h" in files
    assert not any(name.startswith("output_validators/") for name in files)
    assert not any(name.endswith("test_group.yaml") for name in files)
    assert "problem_statement/problem.pdf" not in files
    assert not any(name.startswith("attachments/") for name in files)
    assert b"\r" not in files["problem.yaml"]
    assert "submissions/submissions.yaml" not in files
    for source, target in (("std.cpp", "accepted/std.cpp"), ("wrong.cpp", "rejected/wrong.cpp")):
        assert files[f"submissions/{target}"] == (polygon_dir / "solutions" / source).read_bytes()
    assert files["data/sample/01.desc"] == b'File "01"\n'
    assert LEGACY_WARNING not in caplog.text


@pytest.mark.parametrize("via_cli", [False, True], ids=["api", "cli"])
def test_legacy_warning_once(polygon_dir: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture, via_cli: bool) -> None:
    caplog.set_level(logging.WARNING)
    output = tmp_path / "legacy.zip"
    if via_cli:
        result = CliRunner().invoke(app, [str(polygon_dir), "--code", "A", "--legacy", "-o", str(output), "-y"])
        assert result.exit_code == 0, result.output
        files = read_archive(output)
    else:
        files = export(polygon_dir, output, DomjudgeOptions(legacy=True))
    assert caplog.messages.count(LEGACY_WARNING) == 1
    assert yaml.safe_load(files["problem.yaml"]) == {
        "name": "Little H And Reboot",
        "limits": {"memory": 256},
        "validation": "custom",
    }
    assert "submissions/submissions.yaml" not in files
    assert b"@EXPECTED_RESULTS@: WRONG-ANSWER, TIMELIMIT, RUN-ERROR" in files["submissions/mixed/wrong.cpp"]


@pytest.mark.parametrize("legacy", [False, True])
@pytest.mark.parametrize("auto", [False, True])
@pytest.mark.parametrize("hide_sample", [False, True])
def test_validator_arguments(polygon_dir: Path, tmp_path: Path, legacy: bool, auto: bool, hide_sample: bool) -> None:
    flags = "float_tolerance 1e-4" if auto else "float_tolerance 1e-6"
    files = export(
        polygon_dir,
        tmp_path / "flags.zip",
        DomjudgeOptions(
            legacy=legacy,
            auto_detect_std_checker=auto,
            force_default_validator=not auto,
            validator_flags=None if auto else flags,
            hide_sample=hide_sample,
        ),
    )
    metadata = yaml.safe_load(files["problem.yaml"])
    assert not any(name.startswith("output_validator") for name in files)
    assert ("data/sample/01.in" not in files) == hide_sample
    assert "data/test_group.yaml" not in files
    if legacy:
        assert metadata["validation"] == "default"
        assert metadata["validator_flags"] == flags
        assert not any(name.endswith("test_group.yaml") for name in files)
    else:
        assert metadata["type"] == "pass-fail"
        assert "validation" not in metadata
        assert "validator_flags" not in metadata
        for group in ("sample", "secret"):
            assert yaml.safe_load(files[f"data/{group}/test_group.yaml"]) == {"output_validator_args": flags}


def test_default_validator_without_arguments(polygon_dir: Path, tmp_path: Path) -> None:
    files = export(polygon_dir, tmp_path / "default.zip", DomjudgeOptions(force_default_validator=True))
    assert not any(name.startswith("output_validator") or name.endswith("test_group.yaml") for name in files)


def test_nested_output_directory(polygon_dir: Path, tmp_path: Path) -> None:
    files = export(polygon_dir, tmp_path / "nested" / "output" / "problem.zip")
    assert "problem.yaml" in files


@pytest.mark.parametrize("legacy", [False, True])
@pytest.mark.parametrize(("passes", "interactive"), [(1, True), (2, False), (2, True)])
def test_interaction_modes(fixtures_dir: Path, tmp_path: Path, legacy: bool, passes: int, interactive: bool) -> None:
    package = tmp_path / "interactive"
    with zipfile.ZipFile(fixtures_dir / "guess-array-1$linux.zip") as archive:
        archive.extractall(package)
    tree = ET.parse(package / "problem.xml")
    judging = tree.find("judging")
    assert judging is not None
    judging.set("run-count", str(passes))
    interactor = tree.find("assets/interactor")
    assert interactor is not None
    if passes > 1 and interactive:
        runs = ET.SubElement(interactor, "runs")
        ET.SubElement(runs, "run")
        ET.SubElement(runs, "run")
    tree.write(package / "problem.xml", encoding="utf-8")
    output = tmp_path / "interaction.zip"
    files = export(package, output, DomjudgeOptions(legacy=legacy, auto_detect_std_checker=True))
    metadata = yaml.safe_load(files["problem.yaml"])
    mode = "interactive" if passes == 1 else "interactive multi-pass" if interactive else "multi-pass"
    if legacy:
        assert metadata["validation"] == f"custom {mode}"
        validator = "output_validators/interactor"
    else:
        assert metadata["type"] == mode
        assert "validation" not in metadata
        validator = "output_validator"
    assert f"{validator}/interactor.cpp" in files
    assert f"{validator}/testlib.h" in files
    assert not any(name.startswith("data/sample/") and name.endswith(".in") for name in files)
    if passes > 1:
        assert metadata["limits"]["validation_passes"] == passes
        assert b"-DDOMJUDGE" in files[f"{validator}/build"]
        with zipfile.ZipFile(output) as archive:
            assert (archive.getinfo(f"{validator}/build").external_attr >> 16) & 0o111
    else:
        assert "validation_passes" not in metadata["limits"]


@pytest.mark.parametrize(
    ("rule", "directory"),
    [
        ({"permitted": ["AC"]}, "accepted"),
        ({"required": ["WA", "TLE", "RTE"]}, "rejected"),
        ({"permitted": ["WA", "AC"], "required": ["WA"]}, "wrong_answer"),
        ({"permitted": ["AC", "TLE"], "required": ["TLE"]}, "time_limit_exceeded"),
        ({"permitted": ["AC", "RTE"], "required": ["RTE"]}, "run_time_error"),
        ({"permitted": ["TLE", "AC", "RTE"], "required": ["TLE", "RTE"]}, "brute_force"),
    ],
)
def test_default_submission_directories(polygon_dir: Path, tmp_path: Path, rule: dict[str, list[str]], directory: str) -> None:
    files = export(
        polygon_dir,
        tmp_path / "rules.zip",
        config=GlobalConfig(tag={"main": SubmissionRule(permitted=("AC",)), "rejected": SubmissionRule.model_validate(rule)}),
    )
    assert f"submissions/{directory}/wrong.cpp" in files
    assert "submissions/submissions.yaml" not in files


@pytest.mark.parametrize(
    "rule",
    [
        {"permitted": ["AC", "TLE"]},
        {"permitted": ["AC", "WA", "TLE"], "required": ["TLE"]},
        {"required": ["AC"]},
        {},
    ],
)
def test_custom_submission_rules(polygon_dir: Path, tmp_path: Path, rule: dict[str, list[str]]) -> None:
    files = export(
        polygon_dir,
        tmp_path / "custom.zip",
        config=GlobalConfig(tag={"main": SubmissionRule(permitted=("AC",)), "rejected": SubmissionRule.model_validate(rule)}),
    )
    assert yaml.safe_load(files["submissions/submissions.yaml"]) == {"mixed/wrong.cpp": rule}
    assert files["submissions/mixed/wrong.cpp"] == (polygon_dir / "solutions/wrong.cpp").read_bytes()
    assert "submissions/accepted/std.cpp" in files
    assert "submissions/time_limit_exceeded/wrong.cpp" not in files


@pytest.mark.parametrize("legacy", [False, True])
def test_tag_rules_from_toml(polygon_dir: Path, tmp_path: Path, legacy: bool) -> None:
    config = tmp_path / "rules.toml"
    config.write_text('[tag]\nmain = { permitted = ["AC"] }\nrejected = { permitted = ["AC", "TLE"] }\n', encoding="utf-8")
    output = tmp_path / "configured.zip"
    args = [str(polygon_dir), "--code", "A", "-o", str(output), "--config", str(config), "-y"]
    if legacy:
        args.append("--legacy")
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 0, result.output
    files = read_archive(output)
    if legacy:
        assert "submissions/submissions.yaml" not in files
        assert b"@EXPECTED_RESULTS@: CORRECT, TIMELIMIT" in files["submissions/mixed/wrong.cpp"]
    else:
        assert yaml.safe_load(files["submissions/submissions.yaml"]) == {"mixed/wrong.cpp": {"permitted": ["AC", "TLE"]}}


def test_unknown_tag_and_existing_annotations(polygon_dir: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    source = b"// @EXPECTED_RESULTS@: WRONG-ANSWER\r\n// @EXPECTED_SCORE@: 0\r\nint main() {}\r\n"
    (polygon_dir / "solutions/wrong.cpp").write_bytes(source)
    files = export(polygon_dir, tmp_path / "unknown.zip", config=GlobalConfig(tag={"main": SubmissionRule(permitted=("AC",))}))
    assert files["submissions/rejected/wrong.cpp"] == source
    assert "submissions/submissions.yaml" not in files
    assert "Unknown solution tag rejected" in caplog.text
    assert "DOMjudge also uses these annotations" in caplog.text


@pytest.mark.parametrize(
    "rule",
    [
        SubmissionRule(permitted=("WA",), required=("WA",)),
        SubmissionRule(permitted=("AC", "WA", "TLE"), required=("TLE",)),
        SubmissionRule(required=("AC",)),
    ],
)
def test_legacy_rejects_extra_per_test_requirements(polygon_dir: Path, tmp_path: Path, rule: SubmissionRule) -> None:
    output = tmp_path / "unsupported.zip"
    with pytest.raises(ProcessError, match="Legacy export cannot represent.*rejected"):
        export(polygon_dir, output, DomjudgeOptions(legacy=True), GlobalConfig(tag={"rejected": rule}))
    assert not output.exists()


def test_legacy_brute_force_rule(polygon_dir: Path, tmp_path: Path) -> None:
    files = export(
        polygon_dir,
        tmp_path / "legacy-brute-force.zip",
        DomjudgeOptions(legacy=True),
        GlobalConfig(tag={"rejected": SubmissionRule(permitted=("AC", "RTE", "TLE"), required=("RTE", "TLE"))}),
    )
    assert b"@EXPECTED_RESULTS@: TIMELIMIT, RUN-ERROR" in files["submissions/mixed/wrong.cpp"]


def test_legacy_requires_comment_syntax(polygon_dir: Path, tmp_path: Path) -> None:
    with pytest.raises(ProcessError, match="comment_str is not configured for cpp"):
        export(polygon_dir, tmp_path / "missing-syntax.zip", DomjudgeOptions(legacy=True), GlobalConfig(comment_str={}))


@pytest.mark.parametrize("legacy", [False, True])
def test_optional_identity_for_legacy(polygon_dir: Path, tmp_path: Path, legacy: bool) -> None:
    tree = ET.parse(polygon_dir / "problem.xml")
    del tree.getroot().attrib["url"]
    tree.write(polygon_dir / "problem.xml", encoding="utf-8")
    if legacy:
        export(polygon_dir, tmp_path / "legacy.zip", DomjudgeOptions(legacy=True))
    else:
        with pytest.raises(ProcessError, match="Polygon problem URL"):
            export(polygon_dir, tmp_path / "2025-09.zip")


def test_stable_identity_and_fractional_limits(polygon_dir: Path, tmp_path: Path) -> None:
    original = yaml.safe_load(export(polygon_dir, tmp_path / "original.zip")["problem.yaml"])
    tree = ET.parse(polygon_dir / "problem.xml")
    tree.getroot().set("short-name", "renamed")
    tree.getroot().set("revision", "99")
    time_limit = tree.find("judging/testset/time-limit")
    name = tree.find('names/name[@language="english"]')
    assert time_limit is not None and name is not None
    time_limit.text = "1501"
    name.set("value", "Renamed Problem")
    tree.write(polygon_dir / "problem.xml", encoding="utf-8")
    files = export(
        polygon_dir,
        tmp_path / "changed.zip",
        DomjudgeOptions(memory_limit_override=-1, output_limit_override=64),
        short_name="B",
    )
    changed = yaml.safe_load(files["problem.yaml"])
    assert changed["uuid"] == original["uuid"]
    assert changed["name"] == "Renamed Problem"
    assert changed["limits"] == {"time_limit": 1.501, "time_resolution": 0.001, "output": 64}
    assert b"timelimit = 1.501\n" in files["domjudge-problem.ini"]


@pytest.mark.parametrize("language", ["english", "chinese", "russian"])
def test_statements_and_attachments(polygon_dir: Path, tmp_path: Path, language: str) -> None:
    tree = ET.parse(polygon_dir / "problem.xml")
    if language == "russian":
        names = tree.find("names")
        assert names is not None
        ET.SubElement(names, "name", {"language": language, "value": "Задача"})
        statements = tree.find("statements")
        assert statements is not None
        ET.SubElement(statements, "statement", {"language": language, "type": "application/pdf", "path": "russian.pdf"})
        (polygon_dir / "russian.pdf").write_bytes(b"%PDF-1.0\n")
    files_node = tree.find("files")
    assert files_node is not None
    attachments = ET.SubElement(files_node, "attachments")
    ET.SubElement(attachments, "file", {"path": "tool.py"})
    (polygon_dir / "tool.py").write_bytes(b"print('tool')\n")
    tree.write(polygon_dir / "problem.xml", encoding="utf-8")
    files = export(
        polygon_dir,
        tmp_path / "resources.zip",
        DomjudgeOptions(with_statement=True, with_attachments=True, hide_sample=True),
        GlobalConfig(language_preference=[language]),
    )
    name = yaml.safe_load(files["problem.yaml"])["name"]
    expected_names = {"english": "Little H And Reboot", "chinese": {"zh": "小 H 的重启"}, "russian": {"ru": "Задача"}}
    assert name == expected_names[language]
    assert files["problem_statement/problem.pdf"].startswith(b"%PDF")
    assert files["attachments/tool.py"] == b"print('tool')\n"


def test_unknown_language(polygon_dir: Path, tmp_path: Path) -> None:
    tree = ET.parse(polygon_dir / "problem.xml")
    names = tree.find("names")
    assert names is not None
    names.clear()
    ET.SubElement(names, "name", {"language": "unknown", "value": "Example"})
    tree.write(polygon_dir / "problem.xml", encoding="utf-8")
    with pytest.raises(ProcessError, match="Unsupported statement language"):
        export(polygon_dir, tmp_path / "language.zip")
