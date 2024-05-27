import pytest


@pytest.mark.parametrize('lang, expected', [
    ('c.gcc', 'c'),
    ('cpp.g++', 'cpp'),
    ('cpp.g++11', 'cpp'),
    ('cpp.g++14', 'cpp'),
    ('cpp.g++17', 'cpp'),
    ('cpp.gcc11-64-winlibs-g++20', 'cpp'),
    ('cpp.ms2017', 'cpp'),
    ('cpp.msys2-mingw64-9-g++17', 'cpp'),
    ('java11', 'java'),
    ('java8', 'java'),
    ('kotlin', 'kotlin'),
    ('kotlin16', 'kotlin'),
    ('kotlin17', 'kotlin'),
    ('kotlin19', 'kotlin'),
    ('python.3', 'python'),
    ('python.pypy3', 'python')
])
def test_get_normalized_lang(lang, expected):

    from p2d.utils import get_normalized_lang
    actual = get_normalized_lang(lang)
    assert actual == expected, f'Expected: {expected}, Actual: {actual}'
