from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from p2d.exceptions import ProcessError
from p2d.utils import ensure_dir

if TYPE_CHECKING:
    from p2d.pipeline import ProcessingContext

logger = logging.getLogger(__name__)

# Testlib header location - can be overridden via TESTLIB_PATH environment variable
_DEFAULT_TESTLIB_DIR = Path(__file__).parent.parent / "testlib"
_TESTLIB_PATH = Path(os.getenv("TESTLIB_PATH", _DEFAULT_TESTLIB_DIR)) / "testlib.h"


def add_metadata(ctx: ProcessingContext) -> None:
    """Generate metadata files (domjudge-problem.ini, problem.yaml, validators)."""
    logger.info("[bold green reverse]Add problem metadata files:[/]", extra={"markup": True})
    _write_ini(ctx)
    _write_yaml(ctx)


def _write_ini(ctx: ProcessingContext) -> None:
    ini_file = ctx.temp_dir / "domjudge-problem.ini"
    ini_content = (
        f"short-name = {ctx.short_name}",
        f"timelimit = {ctx.problem.timelimit}",
        f"color = {ctx.profile.color}",
        f"externalid = {ctx.profile.external_id}",
    )
    for line in ini_content:
        logger.info(line)

    ini_file.write_text("\n".join(ini_content) + "\n", encoding="utf-8")


def _write_yaml(ctx: ProcessingContext) -> None:
    yaml_content = _build_yaml_content(ctx)
    output_validators_dir = ctx.temp_dir / "output_validators"

    _configure_validation_assets(ctx, yaml_content, output_validators_dir)

    logger.info(yaml_content)
    yaml_file = ctx.temp_dir / "problem.yaml"
    yaml_file.write_text(yaml.dump(yaml_content, allow_unicode=True, default_flow_style=False), encoding="utf-8")


def _build_yaml_content(ctx: ProcessingContext) -> dict[str, Any]:
    """Build the problem.yaml content using effective limits from profile."""
    yaml_content: dict[str, Any] = {"name": ctx.problem.name}
    limits: dict[str, int] = {}
    if ctx.profile.memory_limit > 0:
        limits["memory"] = ctx.profile.memory_limit
    if ctx.profile.output_limit > 0:
        limits["output"] = ctx.profile.output_limit
    if limits:
        yaml_content["limits"] = limits
    return yaml_content


# -----------------------------------------------------------------------------
# Validation Configuration
# -----------------------------------------------------------------------------


class _ValidationType:
    """Constants for DOMjudge validation types."""

    DEFAULT = "default"
    CUSTOM = "custom"
    CUSTOM_INTERACTIVE = "custom interactive"
    CUSTOM_MULTI_PASS = "custom multi-pass"  # Experimental: multi-pass validation (DOMjudge 9.0)
    CUSTOM_INTERACTIVE_MULTI_PASS = "custom interactive multi-pass"  # Not implemented yet in DOMjudge yet


def _configure_validation_assets(
    ctx: ProcessingContext,
    yaml_content: dict[str, Any],
    output_validators_dir: Path,
) -> None:
    """Configure validation type and copy necessary validator files.

    This function determines the appropriate validation strategy based on:
    1. Whether to use the standard DOMjudge validator (use_std_checker)
    2. Whether the problem has an interactor (interactive problem)
    3. Whether the problem requires multiple passes (experimental)
    """
    # Case 1: Use DOMjudge's default validator
    if _should_use_default_validation(ctx):
        _configure_default_validation(ctx, yaml_content)
        return

    # Case 2: Multi-pass validation (experimental)
    if ctx.problem.run_count > 1:
        _configure_multi_pass_validation(ctx, yaml_content, output_validators_dir)
        return

    # Case 3: Standard custom validation (single pass)
    _configure_custom_validation(ctx, yaml_content, output_validators_dir)


def _should_use_default_validation(ctx: ProcessingContext) -> bool:
    """Check if we should use DOMjudge's default output validator."""
    # Can't use default validation for interactive problems
    if ctx.problem.interactor is not None:
        return False
    return ctx.profile.use_std_checker


def _configure_default_validation(ctx: ProcessingContext, yaml_content: dict[str, Any]) -> None:
    """Configure default (built-in) DOMjudge validation."""
    checker_name = ctx.problem.checker.name if ctx.problem.checker is not None else "unknown"
    logger.info("Use std checker: %s", checker_name)
    yaml_content["validation"] = _ValidationType.DEFAULT

    if ctx.profile.validator_flags:
        logger.info("Validator flags: %s", ctx.profile.validator_flags)
        yaml_content["validator_flags"] = ctx.profile.validator_flags


def _configure_custom_validation(
    ctx: ProcessingContext,
    yaml_content: dict[str, Any],
    output_validators_dir: Path,
) -> None:
    """Configure custom checker or interactor for single-pass validation."""
    ensure_dir(output_validators_dir)

    if ctx.problem.interactor is not None:
        # Interactive problem
        logger.info("Use custom interactor.")
        yaml_content["validation"] = _ValidationType.CUSTOM_INTERACTIVE
        interactor_file = ctx.package_dir / ctx.problem.interactor.path
        _copy_validator_source(interactor_file, output_validators_dir / "interactor")

    elif ctx.problem.checker is not None:
        # Non-interactive with custom checker
        logger.info("Use custom checker.")
        yaml_content["validation"] = _ValidationType.CUSTOM
        checker_file = ctx.package_dir / ctx.problem.checker.path
        _copy_validator_source(checker_file, output_validators_dir / "checker")

    else:
        msg = "No checker found."
        raise ProcessError(msg)


def _configure_multi_pass_validation(
    ctx: ProcessingContext,
    yaml_content: dict[str, Any],
    output_validators_dir: Path,
) -> None:
    """Configure multi-pass validation (EXPERIMENTAL).

    Multi-pass validation allows the validator to run multiple times,
    which is useful for problems requiring back-and-forth communication.

    Warning:
        This feature requires DOMjudge 8.3+ and is not fully supported.
        Use at your own risk.
    """
    logger.info("Use multiple passes.")
    logger.warning(
        "[bold yellow]Multiple passes is an experimental feature.[/]\n"
        "It requires DOMjudge 8.3+ and is not fully supported.\n"
        "Please ensure you know what you are doing.",
        extra={"markup": True},
    )

    if ctx.problem.interactor is None:
        msg = "Multi-pass validation requires an interactor."
        raise ProcessError(msg)

    # Validate run_count (currently only 2 passes supported)
    if ctx.problem.run_count != 2:
        msg = f"Unsupported run_count: {ctx.problem.run_count}. Only 2 passes are currently supported."
        raise ProcessError(msg)

    # Set validation passes limit
    limits = yaml_content.setdefault("limits", {})
    limits["validation_passes"] = ctx.problem.run_count

    # Determine validation type based on whether it's interactive multi-pass
    if ctx.problem.interactive_multipass:
        logger.info("Interactive multi-pass problem detected.")
        yaml_content["validation"] = _ValidationType.CUSTOM_INTERACTIVE_MULTI_PASS
    else:
        logger.info("Non-interactive multi-pass problem detected.")
        yaml_content["validation"] = _ValidationType.CUSTOM_MULTI_PASS

    # Copy interactor with build script
    ensure_dir(output_validators_dir)
    logger.info("Use custom interactor.")
    interactor_file = ctx.package_dir / ctx.problem.interactor.path
    _copy_validator_source(
        interactor_file,
        output_validators_dir / "interactor",
        create_build_script=True,
    )


# -----------------------------------------------------------------------------
# File Operations
# -----------------------------------------------------------------------------


def _copy_validator_source(
    source_file: Path,
    destination_dir: Path,
    *,
    create_build_script: bool = False,
) -> None:
    """Copy validator/interactor source to destination with testlib.h if needed.

    Args:
        source_file: Path to the source file (checker/interactor).
        destination_dir: Directory to copy files into.
        create_build_script: If True, create a build script for the interactor.
            This is needed for multi-pass validation.
    """
    ensure_dir(destination_dir)

    if source_file.suffix == ".cpp":
        # Copy testlib.h for C++ validators
        shutil.copyfile(_TESTLIB_PATH, destination_dir / "testlib.h")

        if create_build_script:
            _create_build_script(destination_dir, source_file.name)

    shutil.copyfile(source_file, destination_dir / source_file.name)


def _create_build_script(destination_dir: Path, source_filename: str) -> None:
    """Create a build script for compiling the interactor."""
    build_script = destination_dir / "build"
    build_script.write_text(
        f"""#!/bin/sh
# Auto-generated build script for interactor by Polygon2DOMjudge
g++ -Wall -DDOMJUDGE -O2 {source_filename} -std=gnu++20 -o run
""",
    )
    build_script.chmod(0o755)
