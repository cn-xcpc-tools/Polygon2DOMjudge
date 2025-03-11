import errno

import pytest
from typer.testing import CliRunner
from typer import Exit, BadParameter

from p2d.cli import app, validate_external_id, version_callback

runner = CliRunner()


def test_version_callback():
    with pytest.raises(Exit):
        version_callback(True)


def test_validate_external_id():
    # Test valid cases
    assert validate_external_id(None) is None
    assert validate_external_id("problem-1") == "problem-1"
    assert validate_external_id("ABC123") == "ABC123"
    assert validate_external_id("test_123") == "test_123"

    # Test invalid cases
    with pytest.raises(BadParameter):
        validate_external_id("problem@123")
    with pytest.raises(BadParameter):
        validate_external_id("problem.123")
    with pytest.raises(BadParameter):
        validate_external_id("problem/123")


def test_convert_problem_help():
    result = runner.invoke(app, ["problem", "--help"])
    assert result.exit_code == 0
    assert "Process Polygon Package to Domjudge Package" in result.stdout


def test_convert_problem_version():
    result = runner.invoke(app, ["problem", "--version"])
    assert result.exit_code == 0
    assert "Polygon Package to Domjudge Package" in result.stdout


def test_convert_problem_skip_confirmation():
    # Test --yes flag
    result = runner.invoke(app, ["problem", "test.zip", "--code", "test", "-y"])
    assert result.exit_code == errno.ENOENT  # Should fail because test.zip doesn't exist
    assert "Are you sure to convert the package?" not in result.stdout


def test_convert_problem_log_levels():
    for level in ["debug", "info", "warning", "error", "critical"]:
        result = runner.invoke(app, ["problem", "test.zip", "--log-level", level], input="test\n")
        assert result.exit_code == errno.ENOENT  # Should fail because test.zip doesn't exist
