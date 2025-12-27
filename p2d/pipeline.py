from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    from pathlib import Path

    from .models import GlobalConfig
    from .polygon import PolygonProblem


@dataclass(frozen=True, slots=True)
class DomjudgeProfile:
    """Problem specific profile toggles shared across pipeline steps."""

    color: str
    external_id: str
    hide_sample: bool
    keep_sample: Sequence[int] | None
    use_std_checker: bool
    validator_flags: str | None
    with_statement: bool
    with_attachments: bool
    memory_limit_override: int | None
    output_limit_override: int | None


@dataclass(frozen=True, slots=True)
class ProcessingContext:
    """Immutable view over all artifacts needed during processing."""

    package_dir: Path
    temp_dir: Path
    output_file: Path
    short_name: str
    problem: PolygonProblem
    config: GlobalConfig
    profile: DomjudgeProfile


StepCallable: TypeAlias = Callable[[ProcessingContext], None]


@dataclass(frozen=True)
class ProcessStep:
    """Definition of a single processing step."""

    name: str
    handler: StepCallable
    condition: Callable[[ProcessingContext], bool] = lambda _: True

    def should_run(self, ctx: ProcessingContext) -> bool:
        return self.condition(ctx)

    def execute(self, ctx: ProcessingContext) -> None:
        self.handler(ctx)


class ProcessPipeline:
    """Sequential pipeline composed of multiple process steps."""

    def __init__(self, steps: Sequence[ProcessStep]) -> None:
        self._steps = tuple(steps)

    @property
    def steps(self) -> tuple[ProcessStep, ...]:
        return self._steps

    def run(self, ctx: ProcessingContext) -> None:
        for step in self._steps:
            if step.should_run(ctx):
                step.execute(ctx)
