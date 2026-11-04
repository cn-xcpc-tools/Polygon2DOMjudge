from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from p2d import GlobalConfig, SubmissionRule
from p2d.submissions import default_submission_directory
from p2d.utils import load_config


@pytest.mark.parametrize(
    "rule",
    [
        ["accepted"],
        {"permitted": ["accepted"]},
        {"required": ["OLE"]},
        {"required": ["output_limit_exceeded"]},
        {"permitted": []},
        {"required": []},
        {"permitted": ["AC"], "required": ["TLE"]},
        {"permitted": None},
        {"require": ["AC"]},
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


def test_directory_matching_keeps_distinct_requirements() -> None:
    assert default_submission_directory(SubmissionRule(permitted=("AC", "TLE"))) is None
    assert default_submission_directory(SubmissionRule(required=("TLE",))) is None
    assert default_submission_directory(SubmissionRule(permitted=("AC", "RTE", "TLE"), required=("TLE",))) is None


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


def test_example_config_matches_defaults() -> None:
    config = load_config(Path(__file__).parent.parent / "config.example.toml")
    assert config == GlobalConfig()
