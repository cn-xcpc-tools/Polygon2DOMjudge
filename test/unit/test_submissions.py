from typing import Any

import pytest
from pydantic import ValidationError

from p2d import GlobalConfig, SubmissionRule
from p2d.submissions import default_submission_directory


@pytest.mark.parametrize(
    "rule",
    [
        pytest.param(["accepted"], id="list-instead-of-rule"),
        pytest.param({"permitted": ["accepted"]}, id="long-verdict-name"),
        pytest.param({"required": ["OLE"]}, id="unsupported-verdict"),
        pytest.param({"required": ["output_limit_exceeded"]}, id="unsupported-long-verdict"),
        pytest.param({"permitted": []}, id="empty-permitted"),
        pytest.param({"required": []}, id="empty-required"),
        pytest.param({"permitted": ["AC"], "required": ["TLE"]}, id="incompatible-verdicts"),
        pytest.param({"permitted": None}, id="null-permitted"),
        pytest.param({"require": ["AC"]}, id="unknown-field"),
    ],
)
def test_invalid_tag_rules(rule: Any) -> None:
    with pytest.raises(ValidationError):
        GlobalConfig.model_validate({"tag": {"main": rule}})


def test_default_verdict_sets() -> None:
    rule = SubmissionRule()
    assert set(rule.permitted) == {"AC", "WA", "TLE", "RTE"}
    assert set(rule.required) == {"AC", "WA", "TLE", "RTE"}
    assert default_submission_directory(rule) is None


def test_directory_matching_ignores_order_and_duplicates() -> None:
    rule = SubmissionRule(permitted=("TLE", "AC", "RTE", "AC"), required=("TLE", "RTE", "RTE"))
    assert default_submission_directory(rule) == "brute_force"


def test_directory_matching_expands_omitted_defaults() -> None:
    rule = SubmissionRule(permitted=("TLE", "WA", "AC", "RTE"), required=("WA", "RTE", "TLE"))
    assert default_submission_directory(rule) == "rejected"


@pytest.mark.parametrize(
    "rule",
    [
        pytest.param(SubmissionRule(permitted=("AC", "TLE")), id="optional-timeout"),
        pytest.param(SubmissionRule(required=("TLE",)), id="required-timeout"),
        pytest.param(
            SubmissionRule(permitted=("AC", "RTE", "TLE"), required=("TLE",)), id="brute-force-with-required-timeout"
        ),
    ],
)
def test_directory_matching_keeps_distinct_requirements(rule: SubmissionRule) -> None:
    assert default_submission_directory(rule) is None


@pytest.mark.parametrize(
    ("tag", "directory"),
    [
        ("main", "accepted"),
        ("accepted", "accepted"),
        ("wrong-answer", "wrong_answer"),
        ("presentation-error", "wrong_answer"),
        ("time-limit-exceeded", "time_limit_exceeded"),
        ("memory-limit-exceeded", "run_time_error"),
        ("time-limit-exceeded-or-memory-limit-exceeded", "brute_force"),
        ("rejected", "rejected"),
        ("failed", "rejected"),
        ("time-limit-exceeded-or-accepted", None),
    ],
)
def test_default_polygon_tag_mapping(tag: str, directory: str | None) -> None:
    assert default_submission_directory(GlobalConfig().tag[tag]) == directory
