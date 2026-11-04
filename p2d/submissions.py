"""Submission requirements and directory defaults from the 2025-09 format."""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

from .exceptions import ProcessError

type Verdict = Literal["AC", "WA", "TLE", "RTE"]

VERDICTS: tuple[Verdict, ...] = ("AC", "WA", "TLE", "RTE")


class SubmissionRule(BaseModel):
    permitted: tuple[Verdict, ...] = Field(default=VERDICTS, min_length=1)
    required: tuple[Verdict, ...] = Field(default=VERDICTS, min_length=1)

    model_config = {"frozen": True, "extra": "forbid"}

    @model_validator(mode="after")
    def _require_satisfiable_rule(self) -> Self:
        if not set(self.permitted).intersection(self.required):
            raise ValueError("permitted and required must have at least one verdict in common")
        return self

    @property
    def constraints(self) -> tuple[frozenset[Verdict], frozenset[Verdict]]:
        return frozenset(self.permitted), frozenset(self.required)


# Compare both constraints, not just projected final verdicts: for example,
# requiring TLE while permitting WA is different from the default TLE directory.
# https://icpc.io/problem-package-format/spec/2025-09.html#default-directories
DEFAULT_SUBMISSION_RULES = {
    "accepted": SubmissionRule(permitted=("AC",)),
    "rejected": SubmissionRule(required=("RTE", "TLE", "WA")),
    "wrong_answer": SubmissionRule(permitted=("AC", "WA"), required=("WA",)),
    "time_limit_exceeded": SubmissionRule(permitted=("AC", "TLE"), required=("TLE",)),
    "run_time_error": SubmissionRule(permitted=("AC", "RTE"), required=("RTE",)),
    "brute_force": SubmissionRule(permitted=("AC", "RTE", "TLE"), required=("RTE", "TLE")),
}


def default_submission_directory(rule: SubmissionRule) -> str | None:
    return next(
        (directory for directory, default in DEFAULT_SUBMISSION_RULES.items() if rule.constraints == default.constraints), None
    )


def legacy_verdicts(rule: SubmissionRule, tag: str) -> tuple[Verdict, ...]:
    permitted, required = rule.constraints
    # Legacy tags described an allowed final-result set. Support their original
    # shapes: optional failure, or at least one of the permitted failures. More
    # specific per-test requirements have no equivalent in that configuration.
    # Even these supported shapes inherit DOMjudge's first-failure limitation:
    # https://github.com/DOMjudge/domjudge/blob/071e3bafce3828a5cd32b5f4e41598705cbb6c72/webapp/src/Utils/SubmissionsYaml.php#L204
    if "AC" in permitted:
        if permitted <= required:
            return tuple(verdict for verdict in VERDICTS if verdict in permitted)
        failures = permitted - {"AC"}
        if permitted & required == failures:
            return tuple(verdict for verdict in VERDICTS if verdict in failures)
    raise ProcessError(
        f"Legacy export cannot represent the per-test requirements for solution tag {tag!r}; use the 2025-09 export."
    )
