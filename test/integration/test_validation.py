from pathlib import Path

import pytest
import yaml

from p2d import DomjudgeOptions
from test.helpers.packages import export


@pytest.mark.parametrize("legacy", [False, True], ids=["2025-09", "legacy"])
@pytest.mark.parametrize(
    ("auto", "force_default", "configured_flags", "expected_flags"),
    [
        pytest.param(True, False, None, "float_tolerance 1e-4", id="auto"),
        pytest.param(False, True, "float_tolerance 1e-6", "float_tolerance 1e-6", id="explicit"),
    ],
)
@pytest.mark.parametrize("hide_sample", [False, True], ids=["visible", "hidden"])
def test_validator_arguments(
    polygon_dir: Path,
    tmp_path: Path,
    legacy: bool,
    auto: bool,
    force_default: bool,
    configured_flags: str | None,
    expected_flags: str,
    hide_sample: bool,
) -> None:
    files = export(
        polygon_dir,
        tmp_path / "flags.zip",
        DomjudgeOptions(
            legacy=legacy,
            auto_detect_std_checker=auto,
            force_default_validator=force_default,
            validator_flags=configured_flags,
            hide_sample=hide_sample,
        ),
    )
    metadata = yaml.safe_load(files["problem.yaml"])
    assert not any(name.startswith("output_validator") for name in files)
    assert ("data/sample/01.in" not in files) == hide_sample
    assert "data/test_group.yaml" not in files
    if legacy:
        assert metadata["validation"] == "default"
        assert metadata["validator_flags"] == expected_flags
        assert not any(name.endswith("test_group.yaml") for name in files)
    else:
        assert metadata["type"] == "pass-fail"
        assert "validation" not in metadata
        assert "validator_flags" not in metadata
        for group in ("sample", "secret"):
            assert yaml.safe_load(files[f"data/{group}/test_group.yaml"]) == {"output_validator_args": expected_flags}


def test_default_validator_without_arguments(polygon_dir: Path, tmp_path: Path) -> None:
    files = export(polygon_dir, tmp_path / "default.zip", DomjudgeOptions(force_default_validator=True))
    assert not any(name.startswith("output_validator") or name.endswith("test_group.yaml") for name in files)
