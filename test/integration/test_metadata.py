import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

from p2d import DomjudgeOptions, GlobalConfig, ProcessError
from test.helpers.packages import export


@pytest.fixture
def unidentified_polygon_dir(polygon_dir: Path) -> Path:
    tree = ET.parse(polygon_dir / "problem.xml")
    del tree.getroot().attrib["url"]
    tree.write(polygon_dir / "problem.xml", encoding="utf-8")
    return polygon_dir


def test_legacy_identity_is_optional(unidentified_polygon_dir: Path, tmp_path: Path) -> None:
    files = export(unidentified_polygon_dir, tmp_path / "legacy.zip", DomjudgeOptions(legacy=True))
    assert yaml.safe_load(files["problem.yaml"]) == {
        "name": "Little H And Reboot",
        "limits": {"memory": 256},
        "validation": "custom",
    }


def test_modern_identity_is_required(unidentified_polygon_dir: Path, tmp_path: Path) -> None:
    output = tmp_path / "2025-09.zip"
    with pytest.raises(ProcessError, match="Polygon problem URL"):
        export(unidentified_polygon_dir, output)
    assert not output.exists()


def test_stable_identity_and_fractional_limits(polygon_dir: Path, tmp_path: Path) -> None:
    original = yaml.safe_load(export(polygon_dir, tmp_path / "original.zip")["problem.yaml"])
    tree = ET.parse(polygon_dir / "problem.xml")
    tree.getroot().set("short-name", "renamed")
    tree.getroot().set("revision", "99")
    time_limit = tree.find("judging/testset/time-limit")
    name = tree.find('names/name[@language="english"]')
    assert time_limit is not None and name is not None
    time_limit.text = "1501"
    name.set("value", "Renamed Problem")
    tree.write(polygon_dir / "problem.xml", encoding="utf-8")
    files = export(
        polygon_dir,
        tmp_path / "changed.zip",
        DomjudgeOptions(memory_limit_override=-1, output_limit_override=64),
        short_name="B",
    )
    changed = yaml.safe_load(files["problem.yaml"])
    assert changed["uuid"] == original["uuid"]
    assert changed["name"] == "Renamed Problem"
    assert changed["limits"] == {"time_limit": 1.501, "time_resolution": 0.001, "output": 64}
    assert b"timelimit = 1.501\n" in files["domjudge-problem.ini"]


@pytest.mark.parametrize(
    ("legacy", "expected_name"),
    [
        pytest.param(False, {"zh": "小 H 的重启"}, id="2025-09"),
        pytest.param(True, "小 H 的重启", id="legacy"),
    ],
)
def test_language_preference(polygon_dir: Path, tmp_path: Path, legacy: bool, expected_name: str | dict[str, str]) -> None:
    files = export(
        polygon_dir,
        tmp_path / "localized.zip",
        DomjudgeOptions(legacy=legacy, color="#FF0000"),
        GlobalConfig(language_preference=["russian", "chinese", "english"]),
        testset_name="tests",
    )
    metadata = yaml.safe_load(files["problem.yaml"])
    assert metadata["name"] == expected_name
    assert metadata["limits"]["memory"] == 256
    assert files["domjudge-problem.ini"] == (
        b"short-name = A\ntimelimit = 5.0\ncolor = #FF0000\nexternalid = little-h-reboot\n"
    )
