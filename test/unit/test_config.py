from pathlib import Path
from tomllib import TOMLDecodeError

import pytest
from pydantic import ValidationError

from p2d import GlobalConfig
from p2d.utils import load_config


@pytest.mark.parametrize(
    ("config_file", "exception"),
    [
        pytest.param("config-broken.toml", TOMLDecodeError, id="invalid-toml"),
        pytest.param("config-broken2.toml", ValidationError, id="invalid-config"),
    ],
)
def test_load_broken_config(fixtures_dir: Path, config_file: str, exception: type[Exception]) -> None:
    with pytest.raises(exception):
        load_config(fixtures_dir / config_file)


def test_missing_config(tmp_path: Path) -> None:
    path = tmp_path / "missing.toml"
    with pytest.raises(FileNotFoundError) as exc:
        load_config(path)
    assert Path(exc.value.filename) == path


def test_example_config_matches_defaults() -> None:
    config = load_config(Path(__file__).resolve().parents[2] / "config.example.toml")
    assert config == GlobalConfig()
