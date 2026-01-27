"""Core data models and configuration classes for p2d.

This module defines the fundamental data structures used throughout the
Polygon2DOMjudge conversion process, including user-facing options and
internal configuration models.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Literal, TypeAlias

from pydantic import BaseModel, field_validator

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

DEFAULT_COLOR = "#000000"
"""Default problem color in DOMjudge (black)."""


# -----------------------------------------------------------------------------
# Type Aliases
# -----------------------------------------------------------------------------

Result: TypeAlias = Literal[
    "accepted",
    "wrong_answer",
    "time_limit_exceeded",
    # 'memory_limit_exceeded',   # not used in domjudge
    "output_limit_exceeded",
    "run_time_error",
]
"""Possible verdict results for DOMjudge submissions."""


# -----------------------------------------------------------------------------
# Configuration Models
# -----------------------------------------------------------------------------


class ExamplePathPattern(BaseModel):
    """Pattern for locating sample input/output files in Polygon package."""

    input: str
    output: str

    model_config = {"frozen": True}


class DomjudgeOptions(BaseModel):
    """User-facing options for DOMjudge package generation.

    These options are provided by the user (typically via CLI) to control
    how the Polygon package is converted to DOMjudge format.

    Attributes:
        color: Problem color in DOMjudge (hex format #RRGGBB).
        force_default_validator: Use DOMjudge's default output validator.
        auto_detect_std_checker: Automatically detect if Polygon's standard
            checker can be replaced with DOMjudge's default validator.
        validator_flags: Flags passed to the output validator (only with
            force_default_validator).
        hide_sample: Hide all sample test cases from contestants.
        keep_sample: Indices of samples to keep original output (not from statement).
        external_id: External ID in DOMjudge (defaults to Polygon short-name).
        with_statement: Include PDF statement in the package.
        with_attachments: Include attachments in the package.
        memory_limit_override: Override memory limit (MB), -1 uses DOMjudge default.
        output_limit_override: Override output limit (MB), -1 uses DOMjudge default.
    """

    color: str = DEFAULT_COLOR
    force_default_validator: bool = False
    auto_detect_std_checker: bool = False
    validator_flags: str | None = None
    hide_sample: bool = False
    keep_sample: Sequence[int] | None = None
    external_id: str | None = None
    with_statement: bool = False
    with_attachments: bool = False
    memory_limit_override: int | None = None
    output_limit_override: int | None = None

    model_config = {"frozen": True}

    @field_validator("keep_sample", mode="before")
    @classmethod
    def _convert_keep_sample(cls, v: Sequence[int] | None) -> tuple[int, ...] | None:
        """Convert keep_sample to immutable tuple."""
        if v is None:
            return None
        return tuple(v)

    def validate_options(self) -> None:
        """Validate the option combinations.

        Raises:
            ValueError: If incompatible options are specified.
        """
        if not self.force_default_validator and self.validator_flags is not None:
            logger.warning("You are not using default validation, validator flags will be ignored.")

        if self.force_default_validator and self.auto_detect_std_checker:
            msg = "Can not use auto_detect_std_checker and force_default_validator at the same time."
            raise ValueError(msg)


class GlobalConfig(BaseModel):
    """Global configuration loaded from config.toml.

    Controls default behaviors for the conversion process, including
    language preferences, checker mappings, and solution tag interpretations.

    Attributes:
        language_preference: Ordered list of preferred languages for problem name/statement.
        flag: Mapping of Polygon standard checker names to DOMjudge validator flags.
        tag: Mapping of Polygon solution tags to expected DOMjudge verdicts.
        example_path_pattern: Path patterns for sample I/O files in Polygon.
        comment_str: Mapping of language identifiers to comment syntax.
    """

    language_preference: list[str] = ["english", "russian", "chinese"]
    flag: dict[str, str] = {
        "fcmp.cpp": "case_sensitive space_change_sensitive",
        "lcmp.cpp": "case_sensitive",
        "rcmp4.cpp": "float_tolerance 1e-4",
        "rcmp6.cpp": "float_tolerance 1e-6",
        "rcmp9.cpp": "float_tolerance 1e-9",
        "wcmp.cpp": "case_sensitive",
    }
    tag: dict[str, list[Result]] = {
        "main": ["accepted"],
        "accepted": ["accepted"],
        "wrong-answer": ["wrong_answer"],
        "presentation-error": ["wrong_answer"],
        "time-limit-exceeded": ["time_limit_exceeded"],
        "time-limit-exceeded-or-accepted": ["time_limit_exceeded", "accepted"],
        "time-limit-exceeded-or-memory-limit-exceeded": [
            "time_limit_exceeded",
            "run_time_error",
        ],
        "memory-limit-exceeded": ["run_time_error"],
        "rejected": ["wrong_answer", "time_limit_exceeded", "run_time_error"],
        "failed": ["wrong_answer", "time_limit_exceeded", "run_time_error"],
    }
    example_path_pattern: ExamplePathPattern = ExamplePathPattern(input="example.%02d", output="example.%02d.a")
    comment_str: dict[str, str] = {
        "c": "//",
        "cpp": "//",
        "java": "//",
        "python": "#",
        "kotlin": "//",
    }

    model_config = {"frozen": True}
