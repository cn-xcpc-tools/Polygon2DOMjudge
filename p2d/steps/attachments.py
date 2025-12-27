from __future__ import annotations

import logging
import shutil
from typing import TYPE_CHECKING

from p2d.utils import ensure_dir

if TYPE_CHECKING:
    from p2d.pipeline import ProcessingContext

logger = logging.getLogger(__name__)


def add_attachments(ctx: ProcessingContext) -> None:
    """Copy additional attachments if present."""
    if not ctx.polygon_problem.attachments:
        logger.warning("No attachments found in problem.xml, skip adding attachments.")
        return

    ensure_dir(ctx.temp_dir / "attachments")
    logger.info("[bold green reverse]Add attachments:[/]", extra={"markup": True})
    for attachment in ctx.polygon_problem.attachments:
        logger.info("* %s", attachment.name)
        shutil.copyfile(
            ctx.package_dir / attachment,
            ctx.temp_dir / "attachments" / attachment.name,
        )
