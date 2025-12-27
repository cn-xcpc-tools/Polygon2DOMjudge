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

DEFAULT_TESTLIB_PATH = Path(__file__).parent.parent / "testlib"
TESTLIB_PATH = (Path(os.getenv("TESTLIB_PATH", DEFAULT_TESTLIB_PATH)) / "testlib.h").resolve()


def add_metadata(ctx: ProcessingContext) -> None:
    """Generate metadata files (domjudge-problem.ini, problem.yaml, validators)."""
    logger.info("[bold green reverse]Add problem metadata files:[/]", extra={"markup": True})
    _write_ini(ctx)
    _write_yaml(ctx)


def _write_ini(ctx: ProcessingContext) -> None:
    ini_file = ctx.temp_dir / "domjudge-problem.ini"
    ini_content = (
        f"short-name = {ctx.short_name}",
        f"timelimit = {ctx.polygon_problem.timelimit}",
        f"color = {ctx.color}",
        f"externalid = {ctx.external_id}",
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
    yaml_content: dict[str, Any] = {"name": ctx.polygon_problem.name}
    limits: dict[str, int] = {}
    if ctx.polygon_problem.memorylimit > 0:
        limits["memory"] = ctx.polygon_problem.memorylimit
    if ctx.polygon_problem.outputlimit > 0:
        limits["output"] = ctx.polygon_problem.outputlimit
    if limits:
        yaml_content["limits"] = limits
    return yaml_content


def _configure_validation_assets(
    ctx: ProcessingContext,
    yaml_content: dict[str, Any],
    output_validators_dir: Path,
) -> None:
    checker_dir = output_validators_dir / "checker"
    interactor_dir = output_validators_dir / "interactor"
    passlimit = ctx.polygon_problem.run_count

    if ctx.polygon_problem.interactor is None and ctx.use_std_checker:
        checker_name = ctx.polygon_problem.checker.name if ctx.polygon_problem.checker is not None else "unknown"
        logger.info("Use std checker: %s", checker_name)
        yaml_content["validation"] = "default"
        if ctx.validator_flags:
            logger.info("Validator flags: %s", ctx.validator_flags)
            yaml_content["validator_flags"] = ctx.validator_flags
        return

    if passlimit == 1:
        ensure_dir(output_validators_dir)
        if ctx.polygon_problem.interactor is not None:
            logger.info("Use custom interactor.")
            yaml_content["validation"] = "custom interactive"
            interactor_file = ctx.package_dir / ctx.polygon_problem.interactor.path
            _copy_validator_source(interactor_file, interactor_dir)
        elif ctx.polygon_problem.checker is not None:
            logger.info("Use custom checker.")
            yaml_content["validation"] = "custom"
            checker_file = ctx.package_dir / ctx.polygon_problem.checker.path
            _copy_validator_source(checker_file, checker_dir)
        else:
            logger.error("No checker found.")
            msg = "No checker found."
            raise ProcessError(msg)
        return

    _configure_multi_pass_validation(ctx, yaml_content, output_validators_dir, interactor_dir)


def _configure_multi_pass_validation(
    ctx: ProcessingContext,
    yaml_content: dict[str, Any],
    output_validators_dir: Path,
    interactor_dir: Path,
) -> None:
    logger.info("Use multiple passes.")
    logger.warning(
        "Multiple passes is an experimental feature.\nIt is not fully supported by DOMjudge.\nPlease ensure what you are doing.",
    )
    assert ctx.polygon_problem.run_count == 2
    limits = yaml_content.setdefault("limits", {})
    limits["validation_passes"] = ctx.polygon_problem.run_count
    yaml_content["validation"] = "custom multi-pass"
    ensure_dir(output_validators_dir)
    if ctx.polygon_problem.interactor is None:
        logger.error("No interactor found.")
        msg = "No interactor found, not supported in multi-pass validation."
        raise ProcessError(msg)
    logger.info("Use custom interactor.")
    interactor_file = ctx.package_dir / ctx.polygon_problem.interactor.path
    _copy_validator_source(interactor_file, interactor_dir, create_build_script=True)


def _copy_validator_source(
    source_file: Path,
    destination_dir: Path,
    *,
    create_build_script: bool = False,
) -> None:
    ensure_dir(destination_dir)
    if source_file.suffix == ".cpp":
        shutil.copyfile(TESTLIB_PATH, destination_dir / "testlib.h")
        if create_build_script:
            build_script = destination_dir / "build"
            build_script.write_text(
                f"""#!/bin/sh
# Auto-generated build script for interactor by Polygon2DOMjudge
g++ -Wall -DDOMJUDGE -O2 {source_file.name} -std=gnu++20 -o run
""",
            )
            build_script.chmod(0o755)
    shutil.copyfile(source_file, destination_dir / source_file.name)
