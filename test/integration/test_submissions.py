from pathlib import Path

import pytest
import yaml

from p2d import DomjudgeOptions, GlobalConfig, ProcessError, SubmissionRule
from test.helpers.packages import export


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
        pytest.param({"permitted": ["AC", "TLE"]}, id="optional-timeout"),
        pytest.param({"permitted": ["AC", "WA", "TLE"], "required": ["TLE"]}, id="timeout-with-wrong-answer"),
        pytest.param({"required": ["AC"]}, id="required-accepted"),
        pytest.param({}, id="unrestricted"),
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
        pytest.param(SubmissionRule(permitted=("WA",), required=("WA",)), id="all-wrong-answer"),
        pytest.param(SubmissionRule(permitted=("AC", "WA", "TLE"), required=("TLE",)), id="timeout-with-wrong-answer"),
        pytest.param(SubmissionRule(required=("AC",)), id="required-accepted"),
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
    output = tmp_path / "missing-syntax.zip"
    with pytest.raises(ProcessError, match="comment_str is not configured for cpp"):
        export(polygon_dir, output, DomjudgeOptions(legacy=True), GlobalConfig(comment_str={}))
    assert not output.exists()
