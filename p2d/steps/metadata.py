from __future__ import annotations

import logging
import os
import shlex
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from p2d.exceptions import ProcessError
from p2d.formats import PackageFormat, write_yaml
from p2d.utils import ensure_dir

if TYPE_CHECKING:
    from p2d.pipeline import ProcessingContext

logger = logging.getLogger(__name__)

_DEFAULT_TESTLIB_DIR = Path(__file__).parent.parent / "testlib"
_TESTLIB_PATH = Path(os.getenv("TESTLIB_PATH", _DEFAULT_TESTLIB_DIR)) / "testlib.h"


def add_metadata(ctx: ProcessingContext) -> None:
    logger.info("[bold green reverse]Add problem metadata files:[/]", extra={"markup": True})
    package_format = ctx.profile.package_format
    metadata = package_format.problem_metadata(ctx.problem, ctx.profile)
    use_default = ctx.profile.use_std_checker and ctx.problem.interactor is None
    multi_pass = ctx.problem.run_count > 1 and not use_default
    interactive = ctx.problem.interactor is not None and (not multi_pass or ctx.problem.interactive_multipass)

    if multi_pass:
        if ctx.problem.interactor is None:
            raise ProcessError("Multi-pass validation requires an interactor.")
        if ctx.problem.run_count != 2:
            raise ProcessError(f"Unsupported run_count: {ctx.problem.run_count}. Only 2 passes are currently supported.")
        metadata.setdefault("limits", {})["validation_passes"] = ctx.problem.run_count
        logger.warning(
            "Multi-pass conversion is experimental; the interactor must implement the DOMjudge nextpass.in protocol."
        )
        if interactive and package_format is PackageFormat.LEGACY:
            logger.warning(
                "Legacy 'validation: custom interactive multi-pass' is not recognized by the current DOMjudge importer."
            )

    metadata.update(package_format.validation_metadata(custom=not use_default, interactive=interactive, multi_pass=multi_pass))
    if use_default:
        logger.info("Use default output validator.")
        if ctx.profile.validator_flags:
            package_format.configure_validator_args(ctx.temp_dir, metadata, ctx.profile.validator_flags)
    else:
        executable = ctx.problem.interactor if ctx.problem.interactor is not None else ctx.problem.checker
        if executable is None:
            raise ProcessError("No checker found.")
        role = "interactor" if ctx.problem.interactor is not None else "checker"
        logger.info("Use custom %s.", role)
        _copy_validator_source(
            ctx.package_dir / executable.path,
            ctx.temp_dir / package_format.validator_path(role),
            create_build_script=multi_pass,
        )

    _write_ini(ctx)
    logger.info(metadata)
    write_yaml(ctx.temp_dir / "problem.yaml", metadata)


def _write_ini(ctx: ProcessingContext) -> None:
    ini_content = (
        f"short-name = {ctx.short_name}",
        f"timelimit = {ctx.problem.timelimit}",
        f"color = {ctx.profile.color}",
        f"externalid = {ctx.profile.external_id}",
    )
    for line in ini_content:
        logger.info(line)
    ensure_dir(ctx.temp_dir)
    (ctx.temp_dir / "domjudge-problem.ini").write_text("\n".join(ini_content) + "\n", encoding="utf-8", newline="\n")


def _copy_validator_source(source_file: Path, destination_dir: Path, *, create_build_script: bool) -> None:
    ensure_dir(destination_dir)
    if source_file.suffix == ".cpp":
        shutil.copyfile(_TESTLIB_PATH, destination_dir / "testlib.h")
        if create_build_script:
            build_script = destination_dir / "build"
            build_script.write_text(
                f"#!/bin/sh\ng++ -Wall -DDOMJUDGE -O2 {shlex.quote(source_file.name)} -std=gnu++20 -o run\n",
                encoding="utf-8",
                newline="\n",
            )
            build_script.chmod(0o755)
    shutil.copyfile(source_file, destination_dir / source_file.name)
