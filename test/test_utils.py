import sys

if sys.version_info < (3, 11):
    from tomli import TOMLDecodeError
else:
    from tomllib import TOMLDecodeError

from pathlib import Path

import pytest
from pydantic import ValidationError


@pytest.mark.parametrize(
    "lang, expected",
    [
        ("c.gcc", "c"),
        ("cpp.g++", "cpp"),
        ("cpp.g++11", "cpp"),
        ("cpp.g++14", "cpp"),
        ("cpp.g++17", "cpp"),
        ("cpp.gcc11-64-winlibs-g++20", "cpp"),
        ("cpp.ms2017", "cpp"),
        ("cpp.msys2-mingw64-9-g++17", "cpp"),
        ("java11", "java"),
        ("java8", "java"),
        ("kotlin", "kotlin"),
        ("kotlin16", "kotlin"),
        ("kotlin17", "kotlin"),
        ("kotlin19", "kotlin"),
        ("python.3", "python"),
        ("python.pypy3", "python"),
    ],
)
def test_get_normalized_lang(lang: str, expected: str) -> None:
    from p2d.utils import get_normalized_lang

    actual = get_normalized_lang(lang)
    assert actual == expected, f"Expected: {expected}, Actual: {actual}"


@pytest.mark.parametrize(
    "config_file, exception",
    [
        ("config-not-exist.toml", FileNotFoundError),
        ("config-broken.toml", TOMLDecodeError),
        ("config-broken2.toml", ValidationError),
    ],
)
def test_load_broken_config(config_file: str, exception: BaseException) -> None:
    from p2d.utils import load_config

    with pytest.raises(exception):
        load_config(Path(__file__).parent / "test_data" / config_file)
