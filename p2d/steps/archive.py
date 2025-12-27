from __future__ import annotations

import logging
import shutil
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from p2d.pipeline import ProcessingContext

logger = logging.getLogger(__name__)


def make_archive(ctx: ProcessingContext) -> None:
    """Create the final zip archive."""
    logger.info("[bold green reverse]Create archive:[/]", extra={"markup": True})
    shutil.make_archive(ctx.output_file.as_posix(), "zip", ctx.temp_dir)
    logger.info("Make package %s.zip success.", ctx.output_file.name)
