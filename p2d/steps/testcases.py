from __future__ import annotations

import logging
import shutil
from typing import TYPE_CHECKING

from p2d.exceptions import ProcessError
from p2d.models import ProblemType
from p2d.utils import ensure_dir

if TYPE_CHECKING:
    from pathlib import Path

    from p2d.pipeline import ProcessingContext

logger = logging.getLogger(__name__)


def _select_sample_output(ctx: ProcessingContext, idx: int, input_src: Path, output_src: Path) -> Path:
    statement_dir = ctx.package_dir / "statements" / ctx.problem.language
    sample_input_src = statement_dir / (ctx.config.example_path_pattern.input % idx)
    sample_output_src = statement_dir / (ctx.config.example_path_pattern.output % idx)
    if sample_input_src.exists() and input_src.read_bytes() != sample_input_src.read_bytes():
        logger.warning(
            "Input file %s is different from the sample input file, please check it manually.",
            input_src.name,
        )
    if sample_output_src.exists() and output_src.read_bytes() != sample_output_src.read_bytes():
        keep_original = ctx.profile.keep_sample is not None and idx in ctx.profile.keep_sample
        logger.warning(
            "Output file %s is different from the sample output file, %s.",
            output_src.name,
            "keep the original output" if keep_original else "use the sample output",
        )
        if not keep_original:
            return sample_output_src
    return output_src


def add_testcases(ctx: ProcessingContext) -> None:
    """Copy tests into DOMjudge structure."""
    logger.info("[bold green reverse]Add tests:[/]", extra={"markup": True})

    ensure_dir(ctx.temp_dir / "data" / "sample")
    ensure_dir(ctx.temp_dir / "data" / "secret")
    for idx, test in enumerate(ctx.problem.test_cases, 1):
        input_src = ctx.package_dir / (ctx.problem.input_path_pattern % idx)
        output_src = ctx.package_dir / (ctx.problem.answer_path_pattern % idx)
        is_sample = test.sample and not ctx.profile.hide_sample
        group = "sample" if is_sample else "secret"
        data_dir = ctx.temp_dir / "data" / group

        if is_sample:
            if ctx.profile.problem_types == {ProblemType.PASS_FAIL}:
                output_src = _select_sample_output(ctx, idx, input_src, output_src)
            elif ctx.problem.use_interaction_log_in_example_tests:
                example_name = ctx.config.example_path_pattern.input % idx
                interaction_src = ctx.package_dir / "statements" / ctx.problem.language / f"{example_name}.i"
                try:
                    shutil.copyfile(interaction_src, data_dir / f"{idx:02d}.interaction")
                except FileNotFoundError as exc:
                    raise ProcessError(f"Sample interaction log is missing: {interaction_src}") from exc

        logger.log(logging.INFO if is_sample else logging.DEBUG, "* %s: %02d.(in/ans) %s", group, idx, test.method)

        if ctx.profile.output_limit > 0 and output_src.stat().st_size > ctx.profile.output_limit * 1048576:
            logger.warning("Output file %s exceeds the output limit.", output_src.name)

        shutil.copyfile(input_src, data_dir / f"{idx:02d}.in")
        shutil.copyfile(output_src, data_dir / f"{idx:02d}.ans")

        test_description = str(test).strip()
        if test_description:
            logger.debug(test_description)
            (data_dir / f"{idx:02d}.desc").write_text(test_description + "\n", encoding="utf-8", newline="\n")
    logger.info("Total %d tests.", len(ctx.problem.test_cases))
