"""Processing pipeline infrastructure for Polygon to DOMjudge conversion.

This module defines the pipeline architecture used to process Polygon packages
into DOMjudge format. The pipeline consists of sequential steps, each performing
a specific transformation or file generation task.

Key components:
    - DomjudgeProfile: Derived configuration for a specific problem conversion
    - ProcessingContext: Immutable context passed to each pipeline step
    - ProcessStep: Individual step definition with optional condition
    - ProcessPipeline: Orchestrates step execution
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    from pathlib import Path

    from .models import GlobalConfig
    from .polygon import PolygonProblem

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DomjudgeProfile:
    """Derived configuration for DOMjudge package generation.

    This profile is derived from user-provided DomjudgeOptions and represents
    the resolved settings after applying defaults and automatic adjustments
    (e.g., forcing hide_sample for interactive problems).

    Attributes:
        color: Problem color in DOMjudge (hex format).
        external_id: Problem external ID in DOMjudge.
        hide_sample: Whether to hide sample test cases.
        keep_sample: Indices of samples to keep original output.
        use_std_checker: Use DOMjudge's default output validator.
        validator_flags: Flags for the output validator.
        with_statement: Include PDF statement in package.
        with_attachments: Include attachments in package.
        memory_limit: Effective memory limit (MB), -1 means use DOMjudge default.
        output_limit: Effective output limit (MB), -1 means use DOMjudge default.
    """

    color: str
    external_id: str
    hide_sample: bool
    keep_sample: Sequence[int] | None
    use_std_checker: bool
    validator_flags: str | None
    with_statement: bool
    with_attachments: bool
    memory_limit: int
    output_limit: int


@dataclass(frozen=True, slots=True)
class ProcessingContext:
    """Immutable context passed to each pipeline step.

    Contains all the information needed by processing steps to perform
    their work, including paths, problem metadata, and configuration.

    Attributes:
        package_dir: Path to the extracted Polygon package.
        temp_dir: Temporary directory for building the DOMjudge package.
        output_file: Output path for the final archive (without .zip).
        short_name: Problem short name in DOMjudge.
        problem: Parsed Polygon problem metadata.
        config: Global conversion configuration.
        profile: Derived DOMjudge profile for this conversion.
    """

    package_dir: Path
    temp_dir: Path
    output_file: Path
    short_name: str
    problem: PolygonProblem
    config: GlobalConfig
    profile: DomjudgeProfile


StepCallable: TypeAlias = Callable[[ProcessingContext], None]
"""Type alias for step handler functions."""


@dataclass(frozen=True)
class ProcessStep:
    """Definition of a single processing step.

    Each step has a name, a handler function, and an optional condition
    that determines whether the step should run.

    Attributes:
        name: Identifier for the step (used for logging/debugging).
        handler: Function to execute for this step.
        condition: Predicate that returns True if the step should run.
    """

    name: str
    handler: StepCallable
    condition: Callable[[ProcessingContext], bool] = lambda _: True

    def should_run(self, ctx: ProcessingContext) -> bool:
        """Check if this step should run given the context."""
        return self.condition(ctx)

    def execute(self, ctx: ProcessingContext) -> None:
        """Execute the step handler."""
        self.handler(ctx)


class ProcessPipeline:
    """Sequential pipeline composed of multiple processing steps.

    The pipeline executes steps in order, skipping any step whose
    condition returns False.

    Example:
        >>> pipeline = ProcessPipeline([
        ...     ProcessStep("step1", handler1),
        ...     ProcessStep("step2", handler2, condition=lambda ctx: ctx.profile.with_statement),
        ... ])
        >>> pipeline.run(context)
    """

    def __init__(self, steps: Sequence[ProcessStep]) -> None:
        """Initialize the pipeline with a sequence of steps."""
        self._steps = tuple(steps)

    @property
    def steps(self) -> tuple[ProcessStep, ...]:
        """The steps in this pipeline."""
        return self._steps

    def run(self, ctx: ProcessingContext) -> None:
        """Execute all applicable steps in sequence."""
        for step in self._steps:
            if step.should_run(ctx):
                logger.debug("Running step: %s", step.name)
                step.execute(ctx)
