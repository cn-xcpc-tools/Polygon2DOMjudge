"""Serialization rules for the 2025-09 DOMjudge package format and legacy exports."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import NAMESPACE_URL, uuid5

import yaml

from .exceptions import ProcessError

if TYPE_CHECKING:
    from .pipeline import DomjudgeProfile
    from .polygon import PolygonProblem

LANGUAGE_CODES = {"english": "en", "russian": "ru", "chinese": "zh"}


def write_yaml(path: Path, content: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(content, allow_unicode=True, sort_keys=False), encoding="utf-8", newline="\n")


class PackageFormat(StrEnum):
    V2025_09 = "2025-09"
    LEGACY = "legacy"

    def problem_metadata(self, problem: PolygonProblem, profile: DomjudgeProfile) -> dict[str, Any]:
        metadata: dict[str, Any] = {"name": problem.name}
        limits: dict[str, int | float] = {}
        if self is PackageFormat.V2025_09:
            if not problem.url:
                raise ProcessError("Polygon problem URL is required to generate a stable UUID for the 2025-09 format.")
            try:
                language = LANGUAGE_CODES[problem.language]
            except KeyError as exc:
                raise ProcessError(f"Unsupported statement language for the 2025-09 format: {problem.language}") from exc
            metadata = {
                "problem_format_version": self.value,
                "uuid": str(uuid5(NAMESPACE_URL, problem.url)),
                "name": problem.name if language == "en" else {language: problem.name},
            }
            limits.update(time_limit=problem.timelimit, time_resolution=0.001)
        if profile.memory_limit > 0:
            limits["memory"] = profile.memory_limit
        if profile.output_limit > 0:
            limits["output"] = profile.output_limit
        if limits:
            metadata["limits"] = limits
        return metadata

    def validation_metadata(self, *, custom: bool, interactive: bool, multi_pass: bool) -> dict[str, str]:
        modifiers = [name for name, enabled in (("interactive", interactive), ("multi-pass", multi_pass)) if enabled]
        if self is PackageFormat.LEGACY:
            return {"validation": " ".join(["custom" if custom else "default", *modifiers])}

        # DOMjudge splits `type` on spaces; YAML sequences cause a PHP TypeError.
        # Both flags reach the interactive runner and the outer pass loop independently.
        # https://github.com/DOMjudge/domjudge/blob/071e3bafce3828a5cd32b5f4e41598705cbb6c72/webapp/src/Service/ImportProblemService.php#L1372
        # https://github.com/DOMjudge/domjudge/blob/071e3bafce3828a5cd32b5f4e41598705cbb6c72/judge/judgedaemon.main.php#L2453
        return {"type": " ".join(modifiers) if modifiers else "pass-fail"}

    def validator_path(self, role: str) -> Path:
        return Path("output_validators", role) if self is PackageFormat.LEGACY else Path("output_validator")

    def configure_validator_args(self, directory: Path, metadata: dict[str, Any], flags: str) -> None:
        if self is PackageFormat.LEGACY:
            metadata["validator_flags"] = flags
            return

        # The specification requires a sequence, but DOMjudge forwards this value
        # to a string-typed setter. Keep the arguments intact for its shell parser.
        # https://github.com/DOMjudge/domjudge/blob/071e3bafce3828a5cd32b5f4e41598705cbb6c72/webapp/src/Service/ImportProblemService.php#L1291
        # https://github.com/DOMjudge/domjudge/blob/071e3bafce3828a5cd32b5f4e41598705cbb6c72/webapp/src/Entity/TestcaseGroup.php#L195
        for group in ("sample", "secret"):
            write_yaml(directory / "data" / group / "test_group.yaml", {"output_validator_args": flags})
