from __future__ import annotations

import errno
import logging
import os
import sys
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from ._version import __version__
from .exceptions import ProcessError
from .models import GlobalConfig
from .pipeline import ProcessingContext, ProcessPipeline, ProcessStep
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

if sys.version_info < (3, 12):  # pragma: no cover
    from typing_extensions import TypedDict, Unpack
else:  # pragma: no cover
    from typing import TypedDict, Unpack

if TYPE_CHECKING:
    from _typeshed import StrPath

logger = logging.getLogger(__name__)

DEFAULT_COLOR = "#000000"
UNKNOWN = "unknown"


class Polygon2DOMjudge:
    """Polygon to DOMjudge package."""

    def __init__(
        self,
        package_dir: StrPath,
        temp_dir: StrPath,
        output_file: StrPath,
        short_name: str,
        /,
        color: str = DEFAULT_COLOR,
        force_default_validator: bool = False,
        auto_detect_std_checker: bool = False,
        validator_flags: str | None = None,
        hide_sample: bool = False,
        keep_sample: Sequence[int] | None = None,
        testset_name: str | None = None,
        external_id: str | None = None,
        with_statement: bool = False,
        with_attachments: bool = False,
        global_config: GlobalConfig = GlobalConfig(),
        process_pipeline: ProcessPipeline | None = None,
    ) -> None:
        """Initialize the Polygon2DOMjudge class."""
        if not force_default_validator and validator_flags:
            logger.warning("You are not using default validation, validator flags will be ignored.")

        self._package_dir = Path(package_dir)
        self._short_name = short_name
        self._color = color
        self._temp_dir = Path(temp_dir)
        self._output_file = Path(output_file)
        self._with_statement = with_statement
        self._with_attachments = with_attachments
        self._global_config = global_config

        logger.debug("Parse 'problem.xml':")
        if testset_name:
            logger.debug("With testset_name: %s", testset_name)
        self._polygon_problem = PolygonProblem(
            self._package_dir / "problem.xml",
            language_preference=self._global_config.language_preference,
            testset_name=testset_name,
        )
        self._external_id = external_id if external_id else self._polygon_problem.short_name

        if force_default_validator and auto_detect_std_checker:
            logger.error("Can not use auto_detect_std_checker and force_default_validator at the same time.")
            msg = "Can not use auto_detect_std_checker and force_default_validator at the same time."
            raise ValueError(msg)

        self._hide_sample = hide_sample
        if self._polygon_problem.interactor is not None:
            logger.warning("Problem has interactor, hide_sample will be forced enabled.")
            self._hide_sample = True

        self._keep_sample = None
        if not self._hide_sample:
            self._keep_sample = keep_sample
        elif keep_sample is not None:
            logger.warning("Hide sample is enabled, all samples will be hidden, keep_sample will be ignored.")

        self._use_std_checker = (
            auto_detect_std_checker
            and self._polygon_problem.checker is not None
            and self._polygon_problem.checker.name.startswith("std::")
        ) or force_default_validator
        self._validator_flags = None

        if self._use_std_checker:
            if force_default_validator:
                self._validator_flags = validator_flags
            elif self._polygon_problem.checker is not None and self._polygon_problem.checker.name.startswith("std::"):
                self._validator_flags = self._global_config.flag.get(self._polygon_problem.checker.name[5:], None)
            else:
                msg = "Logic error in auto_detect_std_checker."
                raise ProcessError(msg)

        self._process_pipeline: ProcessPipeline = process_pipeline or self._build_default_pipeline()

    def override_memory_limit(self, memory_limit: int) -> Polygon2DOMjudge:
        if not isinstance(memory_limit, int):
            msg = "memory_limit must be an integer."
            raise TypeError(msg)
        if self._polygon_problem.memorylimit == memory_limit:
            return self
        logger.info("Override memory limit: %dMB", memory_limit)
        self._polygon_problem.memorylimit = memory_limit
        return self

    def override_output_limit(self, output_limit: int) -> Polygon2DOMjudge:
        if not isinstance(output_limit, int):
            msg = "output_limit must be an integer."
            raise TypeError(msg)
        if self._polygon_problem.outputlimit == output_limit:
            return self
        logger.info("Override output limit: %dMB", output_limit)
        self._polygon_problem.outputlimit = output_limit
        return self

    def _build_default_pipeline(self) -> ProcessPipeline:
        return ProcessPipeline(
            (
                ProcessStep("add_metadata", add_metadata),
                ProcessStep("add_testcases", add_testcases),
                ProcessStep("add_jury_solutions", add_jury_solutions),
                ProcessStep(
                    "add_statement",
                    add_statement,
                    condition=lambda context: context.with_statement,
                ),
                ProcessStep(
                    "add_attachments",
                    add_attachments,
                    condition=lambda context: context.with_attachments,
                ),
                ProcessStep("archive", make_archive),
            ),
        )

    def process(self) -> None:
        context = self._build_context()
        self._process_pipeline.run(context)

    def _build_context(self) -> ProcessingContext:
        return ProcessingContext(
            package_dir=self._package_dir,
            temp_dir=self._temp_dir,
            output_file=self._output_file,
            short_name=self._short_name,
            color=self._color,
            external_id=self._external_id,
            polygon_problem=self._polygon_problem,
            config=self._global_config,
            hide_sample=self._hide_sample,
            keep_sample=self._keep_sample,
            use_std_checker=self._use_std_checker,
            validator_flags=self._validator_flags,
            with_statement=self._with_statement,
            with_attachments=self._with_attachments,
        )


class ConvertOptions(TypedDict, total=False):
    force_default_validator: bool
    auto_detect_std_checker: bool
    validator_flags: str | None
    hide_sample: bool
    keep_sample: Sequence[int] | None
    testset_name: str | None
    external_id: str | None
    with_statement: bool
    with_attachments: bool


def convert(
    package: StrPath,
    output: StrPath | None = None,
    *,
    short_name: str | None = None,
    color: str = DEFAULT_COLOR,
    memory_limit: int | None = None,
    output_limit: int | None = None,
    global_config: GlobalConfig = GlobalConfig(),
    process_pipeline: ProcessPipeline | None = None,
    confirm: Callable[[], bool] = lambda: True,
    **kwargs: Unpack[ConvertOptions],
) -> None:
    """Convert a Polygon package to a DOMjudge package.

    Args:
        package (StrPath): The path to the polygon package directory.
        output (Optional[StrPath], optional): The path to the output DOMjudge package.
        short_name (Optional[Str], optional): The short name of the problem.
        color (str, optional): The color of the problem.
        memory_limit (Optional[int], optional): Override memory limit in MB.
        output_limit (Optional[int], optional): Override output limit in MB.
        global_config (GlobalConfig, optional): Global configuration.
        process_pipeline (Optional[ProcessPipeline], optional): Custom pipeline to override processing steps.
        confirm (Callable[[], bool], optional): A function to confirm the conversion.

    Raises:
        ProcessError: If convert failed.
        FileNotFoundError: If the package is not found.
        FileExistsError: If the output file already exists.

    """
    logger.info(
        "This is Polygon2DOMjudge by cubercsl.\nProcess Polygon Package to DOMjudge Package.\nVersion: %s",
        __version__,
    )

    if short_name is None:
        msg = "short_name is required."
        raise ValueError(msg)

    global_config = merge_pydantic_models(GlobalConfig(), global_config)

    with (
        tempfile.TemporaryDirectory(prefix="p2d-polygon-") as polygon_temp_dir,
        tempfile.TemporaryDirectory(prefix="p2d-domjudge-") as domjudge_temp_dir,
    ):
        package_dir = resolve_package_dir(package, polygon_temp_dir)
        output_file = resolve_output_file(output, short_name)

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
            color,
            global_config=global_config,
            process_pipeline=process_pipeline,
            **kwargs,
        )

        if memory_limit is not None:
            p.override_memory_limit(memory_limit)
        if output_limit is not None:
            p.override_output_limit(output_limit)

        if confirm():
            p.process()
