"""Main conversion logic for Polygon to DOMjudge package transformation.

This module provides the core conversion functionality through the
`Polygon2DOMjudge` class and the high-level `convert()` function.
"""

from __future__ import annotations

import errno
import logging
import os
import sys
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from .exceptions import ProcessError
from .models import DomjudgeOptions, GlobalConfig
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


# -----------------------------------------------------------------------------
# Default Pipeline Configuration
# -----------------------------------------------------------------------------

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


# -----------------------------------------------------------------------------
# Convert Options
# -----------------------------------------------------------------------------


@dataclass(slots=True)
class ConvertOptions:
    """Configuration bundle for the convert() function.

    Groups together all options needed for a conversion operation,
    separating concerns between output location, global settings,
    problem-specific options, and processing pipeline.

    Attributes:
        output: Output path for the generated package (optional).
        global_config: Global configuration (language preferences, checker flags, etc.).
        process_pipeline: The pipeline of processing steps to execute.
        options: DOMjudge-specific conversion options.
        testset_name: Name of the testset to use (for multi-testset problems).
    """

    output: StrPath | None = None
    global_config: GlobalConfig = field(default_factory=GlobalConfig)
    process_pipeline: ProcessPipeline = field(default_factory=lambda: DEFAULT_PIPELINE)
    options: DomjudgeOptions = field(default_factory=DomjudgeOptions)
    testset_name: str | None = None


# -----------------------------------------------------------------------------
# Main Converter Class
# -----------------------------------------------------------------------------


class Polygon2DOMjudge:
    """Converts a Polygon package to DOMjudge format.

    This class handles the conversion process by:
    1. Parsing the Polygon problem.xml
    2. Deriving a DOMjudge profile from user options
    3. Running the processing pipeline to generate the package

    Attributes:
        profile: The derived DOMjudge profile for this conversion.
    """

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
        """Initialize the converter.

        Args:
            package_dir: Path to the extracted Polygon package.
            temp_dir: Temporary directory for building the DOMjudge package.
            output_file: Output path for the final archive (without .zip).
            short_name: Problem short name in DOMjudge.
            testset_name: Testset to convert (required if multiple testsets exist).
            global_config: Global conversion configuration.
            process_pipeline: Pipeline of processing steps.
            options: DOMjudge-specific options.
        """

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

    @property
    def profile(self) -> DomjudgeProfile:
        """The DOMjudge profile derived from conversion options."""
        return self._profile

    def process(self) -> None:
        """Execute the processing pipeline to generate the DOMjudge package."""
        context = self._build_context()
        self._process_pipeline.run(context)

    def _build_context(self) -> ProcessingContext:
        """Build the processing context for pipeline steps."""
        return ProcessingContext(
            package_dir=self._package_dir,
            temp_dir=self._temp_dir,
            output_file=self._output_file,
            short_name=self._short_name,
            problem=self._problem,
            config=self._global_config,
            profile=self._profile,
        )

    def _derive_profile(self, options: DomjudgeOptions) -> DomjudgeProfile:
        """Derive the internal DOMjudge profile from user options.

        This method translates user-facing options into the internal
        profile used by processing steps, applying validation and
        automatic adjustments as needed.

        Args:
            options: User-provided DOMjudge options.

        Returns:
            A DomjudgeProfile configured for this problem.

        Raises:
            ValueError: If options are invalid.
            ProcessError: If profile derivation fails.
        """
        options.validate_options()

        external_id = options.external_id or self._problem.short_name
        hide_sample = self._resolve_hide_sample(options.hide_sample)
        keep_sample = self._resolve_keep_sample(options.keep_sample, hide_sample)
        use_std_checker, validator_flags = self._resolve_validation(options)
        memory_limit, output_limit = self._resolve_limits(options)

        return DomjudgeProfile(
            color=options.color,
            external_id=external_id,
            hide_sample=hide_sample,
            keep_sample=keep_sample,
            use_std_checker=use_std_checker,
            validator_flags=validator_flags,
            with_statement=options.with_statement,
            with_attachments=options.with_attachments,
            memory_limit=memory_limit,
            output_limit=output_limit,
        )

    def _resolve_hide_sample(self, user_hide_sample: bool) -> bool:
        """Resolve the hide_sample setting, forcing True for interactive problems."""
        if self._problem.interactor is not None:
            logger.warning("Problem has interactor, hide_sample will be forced enabled.")
            return True
        return user_hide_sample

    def _resolve_keep_sample(
        self,
        user_keep_sample: Sequence[int] | None,
        hide_sample: bool,
    ) -> Sequence[int] | None:
        """Resolve which samples to keep, considering hide_sample."""
        if hide_sample:
            if user_keep_sample is not None:
                logger.warning("Hide sample is enabled, all samples will be hidden, keep_sample will be ignored.")
            return None
        return user_keep_sample

    def _resolve_validation(
        self,
        options: DomjudgeOptions,
    ) -> tuple[bool, str | None]:
        """Resolve validation settings (checker vs default validator).

        Returns:
            A tuple of (use_std_checker, validator_flags).

        Raises:
            ProcessError: If validation configuration is inconsistent.
        """
        should_use_std = self._should_use_std_checker(options)

        if not should_use_std:
            return False, None

        # Determine validator flags
        if options.force_default_validator:
            return True, options.validator_flags

        # Auto-detect: derive flags from Polygon checker name
        if self._problem.checker is not None and self._problem.checker.name.startswith("std::"):
            checker_base = self._problem.checker.name[5:]  # Remove "std::" prefix
            flags = self._global_config.flag.get(checker_base)
            return True, flags

        msg = "Logic error in auto_detect_std_checker."
        raise ProcessError(msg)

    def _should_use_std_checker(self, options: DomjudgeOptions) -> bool:
        """Determine if the standard DOMjudge validator should be used."""
        if options.force_default_validator:
            return True

        if not options.auto_detect_std_checker:
            return False

        return self._problem.checker is not None and self._problem.checker.name.startswith("std::")

    def _resolve_limits(self, options: DomjudgeOptions) -> tuple[int, int]:
        """Resolve effective memory and output limits.

        Applies user overrides if specified, otherwise uses problem defaults.
        Logs when overrides differ from problem defaults.

        Returns:
            A tuple of (memory_limit, output_limit) in MB.
            -1 means use DOMjudge's default.
        """
        # Memory limit
        if options.memory_limit_override is not None:
            memory_limit = options.memory_limit_override
            if memory_limit != self._problem.memorylimit:
                logger.info(
                    "Override memory limit: %dMB -> %dMB",
                    self._problem.memorylimit,
                    memory_limit,
                )
        else:
            memory_limit = self._problem.memorylimit

        # Output limit
        if options.output_limit_override is not None:
            output_limit = options.output_limit_override
            if output_limit != self._problem.outputlimit:
                logger.info(
                    "Override output limit: %dMB -> %dMB",
                    self._problem.outputlimit,
                    output_limit,
                )
        else:
            output_limit = self._problem.outputlimit

        return memory_limit, output_limit


# -----------------------------------------------------------------------------
# High-Level API
# -----------------------------------------------------------------------------


def convert(
    package: StrPath,
    *,
    short_name: str,
    options: ConvertOptions = ConvertOptions(),
    confirm: Callable[[], bool] = lambda: True,
) -> None:
    """Convert a Polygon package to a DOMjudge package.

    This is the main entry point for package conversion. It handles:
    - Package extraction (if a zip file is provided)
    - Temporary directory management
    - Output file validation
    - Conversion execution

    Args:
        package: Path to the Polygon package (directory or zip file).
        short_name: Problem short name for DOMjudge.
        options: Conversion configuration bundle.
        confirm: Callback function for user confirmation (returns True to proceed).

    Raises:
        ValueError: If short_name is empty.
        FileNotFoundError: If the package does not exist.
        FileExistsError: If the output file already exists.
        ProcessError: If conversion fails.

    Example:
        >>> from p2d import convert, ConvertOptions, DomjudgeOptions
        >>> convert(
        ...     "problem-package.zip",
        ...     short_name="A",
        ...     options=ConvertOptions(
        ...         options=DomjudgeOptions(color="#FF0000", with_statement=True)
        ...     ),
        ... )
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

        _validate_output_not_exists(output_file)
        _warn_if_windows()

        logger.info("Package directory: %s", package_dir)
        logger.info("Output file: %s.zip", output_file)

        converter = Polygon2DOMjudge(
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
            converter.process()


def _validate_output_not_exists(output_file: Path) -> None:
    """Raise FileExistsError if the output zip file already exists."""
    zip_path = output_file.with_suffix(".zip").resolve()
    if zip_path.exists():
        raise FileExistsError(
            errno.EEXIST,
            os.strerror(errno.EEXIST),
            str(zip_path),
        )


def _warn_if_windows() -> None:
    """Log a warning when running on Windows."""
    if sys.platform.startswith("win"):
        logger.warning("It is not recommended running on windows.")  # pragma: no cover
