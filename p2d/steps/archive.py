from __future__ import annotations

import logging
from stat import S_IFREG
from typing import TYPE_CHECKING
from zipfile import ZIP_DEFLATED, ZipFile

if TYPE_CHECKING:
    from p2d.pipeline import ProcessingContext

logger = logging.getLogger(__name__)


def make_archive(ctx: ProcessingContext) -> None:
    """Create the final zip archive."""
    logger.info("[bold green reverse]Create archive:[/]", extra={"markup": True})
    build_path = ctx.profile.package_format.validator_path("interactor") / "build"
    ctx.output_file.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(f"{ctx.output_file}.zip", "w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(ctx.temp_dir.rglob("*")):
            relative = path.relative_to(ctx.temp_dir)
            archive.write(path, relative)
            if relative == build_path and path.is_file():
                # Windows chmod cannot preserve executable bits required by the
                # judgehost. Record the generated build script's Unix mode in the ZIP.
                info = archive.getinfo(relative.as_posix())
                info.create_system = 3
                info.external_attr = (S_IFREG | 0o755) << 16
    logger.info("Make package %s.zip success.", ctx.output_file.name)
