import logging
from pathlib import Path
from xml.etree.ElementTree import ParseError

import pytest
from typer.testing import CliRunner

from p2d.contest import app


def test_contest(cli_runner: CliRunner, fixtures_dir: Path, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="p2d.contest")
    result = cli_runner.invoke(app, [str(fixtures_dir / "contest.xml")])
    assert result.exit_code == 0, result.output
    messages = [record.getMessage() for record in caplog.records if record.name == "p2d.contest"]
    assert messages == [
        f"Found 3 problems in {fixtures_dir / 'contest.xml'}",
        "Problem A: two-point-removal",
        "Problem B: george-grass",
        "Problem C: divide-and-conquer",
    ]


def test_broken_contest_xml(cli_runner: CliRunner, fixtures_dir: Path) -> None:
    result = cli_runner.invoke(app, [str(fixtures_dir / "contest-broken.xml")])
    assert result.exit_code == 1, result.output
    assert isinstance(result.exception, ParseError)
    assert "unclosed token" in str(result.exception)
