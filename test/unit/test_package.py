from p2d._version import __version__


def test_entrypoint_import() -> None:
    from p2d import __main__

    assert __main__.__name__ == "p2d.__main__"


def test_version() -> None:
    assert __version__
