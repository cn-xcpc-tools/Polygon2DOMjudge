from __future__ import annotations

import string
import sys
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

if sys.version_info < (3, 11):
    import tomli as tomllib  # pragma: no cover
else:
    import tomllib
from deepmerge import always_merger
from pydantic import BaseModel

from .models import GlobalConfig

T = TypeVar("T", bound=BaseModel)

if TYPE_CHECKING:
    from _typeshed import StrPath  # pragma: no cover


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
