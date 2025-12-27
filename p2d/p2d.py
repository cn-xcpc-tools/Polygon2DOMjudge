from __future__ import annotations

import errno
import logging
import os
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from .exceptions import ProcessError
from .models import GlobalConfig
from .pipeline import DomjudgeProfile, ProcessingContext, ProcessPipeline, ProcessStep
from .polygon import PolygonProblem
from .steps import (
    add_attachments,
    add_jury_solutions,
    add_metadata,
    add_statement,
    add_testcases,
    make_archive,
)
from .utils import merge_pydantic_models, resolve_output_file, resolve_package_dir

if TYPE_CHECKING:
    from _typeshed import StrPath

logger = logging.getLogger(__name__)

DEFAULT_COLOR = "#000000"
UNKNOWN = "unknown"

DEFAULT_PIPELINE = ProcessPipeline(
    (
        ProcessStep("add_metadata", add_metadata),
        ProcessStep("add_testcases", add_testcases),
        ProcessStep("add_jury_solutions", add_jury_solutions),
        ProcessStep(
            "add_statement",
            add_statement,
            condition=lambda ctx: ctx.profile.with_statement,
        ),
        ProcessStep(
            "add_attachments",
            add_attachments,
            condition=lambda ctx: ctx.profile.with_attachments,
        ),
        ProcessStep("archive", make_archive),
    ),
)


@dataclass(slots=True)
class DomjudgeOptions:
    color: str = DEFAULT_COLOR
    force_default_validator: bool = False
    auto_detect_std_checker: bool = False
    validator_flags: str | None = None
    hide_sample: bool = False
    keep_sample: tuple[int, ...] | None = None
    external_id: str | None = None
    with_statement: bool = False
    with_attachments: bool = False
    memory_limit_override: int | None = None
    output_limit_override: int | None = None

    def validate(self) -> None:
        if not self.force_default_validator and self.validator_flags is not None:
            logger.warning("You are not using default validation, validator flags will be ignored.")

        if self.force_default_validator and self.auto_detect_std_checker:
            msg = "Can not use auto_detect_std_checker and force_default_validator at the same time."

            raise ValueError(msg)


@dataclass(slots=True)
class ConvertOptions:
    output: StrPath | None = None
    global_config: GlobalConfig = field(default_factory=GlobalConfig)
    process_pipeline: ProcessPipeline = field(default_factory=lambda: DEFAULT_PIPELINE)
    options: DomjudgeOptions = field(default_factory=DomjudgeOptions)
    testset_name: str | None = None


class Polygon2DOMjudge:
    """Polygon to DOMjudge package."""

    def __init__(
        self,
        package_dir: StrPath,
        temp_dir: StrPath,
        output_file: StrPath,
        short_name: str,
        /,
        *,
        testset_name: str | None = None,
        global_config: GlobalConfig = GlobalConfig(),
        process_pipeline: ProcessPipeline = DEFAULT_PIPELINE,
        options: DomjudgeOptions = DomjudgeOptions(),
    ) -> None:
        """Initialize the Polygon2DOMjudge class."""

        self._package_dir = Path(package_dir)
        self._short_name = short_name
        self._temp_dir = Path(temp_dir)
        self._output_file = Path(output_file)
        self._global_config = global_config

        logger.debug("Parse 'problem.xml':")
        if testset_name:
            logger.debug("With testset_name: %s", testset_name)
        self._problem = PolygonProblem(
            self._package_dir / "problem.xml",
            language_preference=self._global_config.language_preference,
            testset_name=testset_name,
        )
        self._profile = self._derive_profile(options)
        self._process_pipeline = process_pipeline

    def process(self) -> None:
        context = self._build_context()
        self._process_pipeline.run(context)

    def _build_context(self) -> ProcessingContext:
        return ProcessingContext(
            package_dir=self._package_dir,
            temp_dir=self._temp_dir,
            output_file=self._output_file,
            short_name=self._short_name,
            problem=self._problem,
            config=self._global_config,
            profile=self._profile,
        )

    @property
    def profile(self) -> DomjudgeProfile:
        return self._profile

    def _derive_profile(self, options: DomjudgeOptions) -> DomjudgeProfile:
        options.validate()

        resolved_external_id = options.external_id if options.external_id else self._problem.short_name

        force_hide_sample = options.hide_sample
        if self._problem.interactor is not None:
            logger.warning("Problem has interactor, hide_sample will be forced enabled.")
            force_hide_sample = True

        effective_keep_sample = None if force_hide_sample else options.keep_sample
        if force_hide_sample and options.keep_sample is not None:
            logger.warning("Hide sample is enabled, all samples will be hidden, keep_sample will be ignored.")

        use_std_checker = (
            options.auto_detect_std_checker
            and self._problem.checker is not None
            and self._problem.checker.name.startswith("std::")
        ) or options.force_default_validator

        derived_flags = None
        if use_std_checker:
            if options.force_default_validator:
                derived_flags = options.validator_flags
            elif self._problem.checker is not None and self._problem.checker.name.startswith("std::"):
                derived_flags = self._global_config.flag.get(self._problem.checker.name[5:], None)
            else:
                msg = "Logic error in auto_detect_std_checker."
                raise ProcessError(msg)

        return DomjudgeProfile(
            color=options.color,
            external_id=resolved_external_id,
            hide_sample=force_hide_sample,
            keep_sample=effective_keep_sample,
            use_std_checker=use_std_checker,
            validator_flags=derived_flags,
            with_statement=options.with_statement,
            with_attachments=options.with_attachments,
            memory_limit_override=options.memory_limit_override,
            output_limit_override=options.output_limit_override,
        )


def convert(
    package: StrPath,
    *,
    short_name: str,
    options: ConvertOptions = ConvertOptions(),
    confirm: Callable[[], bool] = lambda: True,
) -> None:
    """Convert a Polygon package to a DOMjudge package.

    Args:
        package (StrPath): The path to the polygon package directory.
        short_name (str): The short name of the problem within DOMjudge.
        options (Optional[ConvertOptions], optional): Conversion configuration bundle. When not provided,
            defaults are used.
        confirm (Callable[[], bool], optional): A function to confirm the conversion.

    Raises:
        ProcessError: If convert failed.
        FileNotFoundError: If the package is not found.
        FileExistsError: If the output file already exists.

    """
    if not short_name:
        msg = "short_name is required."
        raise ValueError(msg)

    global_config = merge_pydantic_models(GlobalConfig(), options.global_config)

    with (
        tempfile.TemporaryDirectory(prefix="p2d-polygon-") as polygon_temp_dir,
        tempfile.TemporaryDirectory(prefix="p2d-domjudge-") as domjudge_temp_dir,
    ):
        package_dir = resolve_package_dir(package, polygon_temp_dir)
        output_file = resolve_output_file(options.output, short_name)

        if output_file.with_suffix(".zip").resolve().exists():
            raise FileExistsError(
                errno.EEXIST,
                os.strerror(errno.EEXIST),
                f"{output_file.with_suffix('.zip')}",
            )

        if sys.platform.startswith("win"):
            logger.warning("It is not recommended running on windows.")  # pragma: no cover

        logger.info("Package directory: %s", package_dir)
        logger.info("Output file: %s.zip", output_file)

        p = Polygon2DOMjudge(
            package_dir,
            domjudge_temp_dir,
            output_file,
            short_name,
            testset_name=options.testset_name,
            global_config=global_config,
            process_pipeline=options.process_pipeline,
            options=options.options,
        )

        if confirm():
            p.process()
