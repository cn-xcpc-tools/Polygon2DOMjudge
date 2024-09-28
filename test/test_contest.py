from pathlib import Path

from typer.testing import CliRunner

runner = CliRunner()


def test_contest():
    from p2d.contest import app

    contest_xml = Path(__file__).parent / 'test_data' / 'contest.xml'
    result = runner.invoke(app, [str(contest_xml)])
    assert result.exit_code == 0


def test_broken_contest_xml():
    from p2d.contest import app

    contest_xml = Path(__file__).parent / 'test_data' / 'contest-broken.xml'
    result = runner.invoke(app, [str(contest_xml)])
    assert result.exit_code == 1
