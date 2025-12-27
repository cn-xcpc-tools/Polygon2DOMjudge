from __future__ import annotations

import logging
import shutil
from typing import TYPE_CHECKING

from p2d.utils import ensure_dir

if TYPE_CHECKING:
    from p2d.pipeline import ProcessingContext

logger = logging.getLogger(__name__)


def add_statement(ctx: ProcessingContext) -> None:
    """Copy the statement PDF if available."""
    if ctx.problem.statement is None:
        logger.warning("No statement found in problem.xml, skip adding statement.")
        return

    ensure_dir(ctx.temp_dir / "problem_statement")
    logger.info("[bold green reverse]Add statement:[/]", extra={"markup": True})
    logger.info("* %s", ctx.problem.statement)
    shutil.copyfile(
        ctx.package_dir / ctx.problem.statement,
        ctx.temp_dir / "problem_statement" / "problem.pdf",
    )
