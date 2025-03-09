import pytest

from pathlib import Path


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
def test_get_normalized_lang(lang, expected):
    from p2d.utils import get_normalized_lang

    actual = get_normalized_lang(lang)
    assert actual == expected, f"Expected: {expected}, Actual: {actual}"


def test_update_dict():
    from p2d.utils import update_dict

    dict1 = {"a": 1, "b": {"sub1": 1, "sub2": False}, "c": 3}
    dict2 = {"b": {"sub3": "new", "sub2": 47}}
    dict3 = {"a": 0, "b": 12}

    update_dict(dict1, dict2)
    assert dict1 == {"a": 1, "b": {"sub1": 1, "sub2": 47, "sub3": "new"}, "c": 3}

    update_dict(dict1, dict3)
    assert dict1 == {"a": 0, "b": 12, "c": 3}


@pytest.mark.parametrize("config_file", ["config-not-exist.toml", "config-broken.toml"])
def test_load_broken_config(config_file):
    from p2d.utils import load_config

    with pytest.raises(ImportError):
        load_config(Path(__file__).parent / "test_data" / config_file)
