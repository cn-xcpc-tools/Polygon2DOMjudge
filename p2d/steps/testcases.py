from __future__ import annotations

import logging
import shutil
from typing import TYPE_CHECKING

from p2d.utils import ensure_dir

if TYPE_CHECKING:
    from pathlib import Path

    from p2d.pipeline import ProcessingContext

logger = logging.getLogger(__name__)


def _compare(src: Path, dst: Path) -> bool:
    logger.debug("Compare %s and %s", src.name, dst.name)
    return src.read_bytes() != dst.read_bytes()


def add_testcases(ctx: ProcessingContext) -> None:
    """Copy tests into DOMjudge structure."""
    logger.info("[bold green reverse]Add tests:[/]", extra={"markup": True})

    ensure_dir(ctx.temp_dir / "data" / "sample")
    ensure_dir(ctx.temp_dir / "data" / "secret")
    sample_input_path_pattern = ctx.config.example_path_pattern.input
    sample_output_path_pattern = ctx.config.example_path_pattern.output

    for idx, test in enumerate(ctx.problem.test_cases, 1):
        input_src = ctx.package_dir / (ctx.problem.input_path_pattern % idx)
        output_src = ctx.package_dir / (ctx.problem.answer_path_pattern % idx)

        if test.sample and not ctx.profile.hide_sample:
            sample_input_src = ctx.package_dir / "statements" / ctx.problem.language / (sample_input_path_pattern % idx)
            sample_output_src = ctx.package_dir / "statements" / ctx.problem.language / (sample_output_path_pattern % idx)
            if sample_input_src.exists() and _compare(input_src, sample_input_src):
                logger.warning(
                    "Input file %s is different from the sample input file, please check it manually.",
                    input_src.name,
                )
            if sample_output_src.exists() and _compare(output_src, sample_output_src):
                logger.warning(
                    "Output file %s is different from the sample output file, use the sample output.",
                    output_src.name,
                )
                if ctx.profile.keep_sample and idx not in ctx.profile.keep_sample:
                    output_src = sample_output_src
            input_dst = ctx.temp_dir / "data" / "sample" / f"{idx:02d}.in"
            output_dst = ctx.temp_dir / "data" / "sample" / f"{idx:02d}.ans"
            desc_dst = ctx.temp_dir / "data" / "sample" / f"{idx:02d}.desc"

            logger.info("* sample: %02d.(in/ans) %s", idx, test.method)
        else:
            input_dst = ctx.temp_dir / "data" / "secret" / f"{idx:02d}.in"
            output_dst = ctx.temp_dir / "data" / "secret" / f"{idx:02d}.ans"
            desc_dst = ctx.temp_dir / "data" / "secret" / f"{idx:02d}.desc"

            logger.debug("* secret: %02d.(in/ans) %s", idx, test.method)

        if ctx.problem.outputlimit > 0 and output_src.stat().st_size > ctx.problem.outputlimit * 1048576:
            logger.warning("Output file %s is exceed the output limit.", output_src.name)

        shutil.copyfile(input_src, input_dst)
        shutil.copyfile(output_src, output_dst)

        test_description = str(test).strip()
        if test_description:
            logger.debug(test_description)
            desc_dst.write_text(test_description + "\n", encoding="utf-8")
    logger.info("Total %d tests.", len(ctx.problem.test_cases))
