from pathlib import Path

import pytest
from typer.testing import CliRunner


@pytest.fixture
def cli_runner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> CliRunner:
    monkeypatch.chdir(tmp_path)
    return CliRunner()
