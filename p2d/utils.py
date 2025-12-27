from __future__ import annotations

import errno
import logging
import os
import string
import sys
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

if sys.version_info < (3, 11):
    import tomli as tomllib  # pragma: no cover
else:
    import tomllib
if sys.version_info < (3, 12):  # pragma: no cover
    from typing_extensions import TypedDict
else:  # pragma: no cover
    from typing import TypedDict
from deepmerge import always_merger
from pydantic import BaseModel

from .models import GlobalConfig

T = TypeVar("T", bound=BaseModel)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from _typeshed import StrPath  # pragma: no cover


logger = logging.getLogger(__name__)


def ensure_dir(s: Path) -> None:
    if not s.exists():
        s.mkdir(parents=True)


def load_config(config_file: StrPath) -> GlobalConfig:
    return GlobalConfig.model_validate(tomllib.loads(Path(config_file).read_text(encoding="utf-8")))


def merge_pydantic_models(base: T, nxt: T) -> T:
    """Merge two Pydantic model instances.

    The attributes of 'base' and 'nxt' that weren't explicitly set are dumped into dicts
    using '.model_dump(exclude_unset=True)', which are then merged using 'deepmerge',
    and the merged result is turned into a model instance using '.model_validate'.

    For attributes set on both 'base' and 'nxt', the value from 'nxt' will be used in
    the output result.
    """
    base_dict = base.model_dump(exclude_unset=True)
    nxt_dict = nxt.model_dump(exclude_unset=True, exclude_defaults=True)
    merged_dict = always_merger.merge(base_dict, nxt_dict)
    return base.model_validate(merged_dict)


def get_normalized_lang(lang: str) -> str:
    return lang.split(".")[0].rstrip(string.digits)


class Options(TypedDict, total=False):
    force_default_validator: bool
    auto_detect_std_checker: bool
    validator_flags: str | None
    hide_sample: bool
    keep_sample: Sequence[int] | None
    memory_limit: int | None
    output_limit: int | None
    testset_name: str | None
    external_id: str | None
    with_statement: bool
    with_attachments: bool
    test_set: str | None


def resolve_package_dir(package: StrPath, polygon_temp_dir: StrPath) -> Path:
    """Return a ready-to-use package directory, extracting archives when needed."""
    package_path = Path(package)
    if package_path.is_file():
        with zipfile.ZipFile(package_path, "r") as zip_ref:
            logger.info("Extracting %s to %s", package_path.name, polygon_temp_dir)
            extract_path = Path(polygon_temp_dir)
            zip_ref.extractall(extract_path)
            return extract_path
    if package_path.is_dir():
        resolved = package_path.resolve()
        logger.info("Using %s", resolved)
        return resolved
    raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), package_path.name)


def resolve_output_file(output: StrPath | None, short_name: str) -> Path:
    """Resolve the base path (without .zip) for the DOMjudge package."""
    if output:
        output_path = Path(output).resolve()
        if output_path.suffix == ".zip":
            return output_path.with_suffix("")
        return (output_path / short_name).resolve()
    return (Path.cwd() / short_name).resolve()
