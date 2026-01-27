from pathlib import Path

import pytest
from typer import Exit
from typer.testing import CliRunner

from p2d.contest import app, version_callback

runner = CliRunner()


def test_version_callback() -> None:
    with pytest.raises(Exit):
        version_callback(True)


def test_contest(fixtures_dir: Path) -> None:
    contest_xml = fixtures_dir / "contest.xml"
    result = runner.invoke(app, [str(contest_xml)])
    assert result.exit_code == 0


def test_broken_contest_xml(fixtures_dir: Path) -> None:
    contest_xml = fixtures_dir / "contest-broken.xml"
    result = runner.invoke(app, [str(contest_xml)])
    assert result.exit_code == 1
