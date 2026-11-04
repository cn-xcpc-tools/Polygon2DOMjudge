from collections.abc import Callable

import pytest
from typer import BadParameter, Exit

from p2d.cli import validate_external_id, version_callback
from p2d.contest import version_callback as contest_version_callback


@pytest.mark.parametrize("callback", [version_callback, contest_version_callback], ids=["problem", "contest"])
def test_version_callback(callback: Callable[[bool | None], None]) -> None:
    with pytest.raises(Exit) as exc:
        callback(True)
    assert exc.value.exit_code == 0


@pytest.mark.parametrize("value", [None, "problem-1", "ABC123", "test_123"])
def test_valid_external_id(value: str | None) -> None:
    assert validate_external_id(value) == value


@pytest.mark.parametrize("value", ["problem@123", "problem.123", "problem/123"])
def test_invalid_external_id(value: str) -> None:
    with pytest.raises(BadParameter, match="external-id must contain only letters, numbers, hyphens and underscores"):
        validate_external_id(value)
