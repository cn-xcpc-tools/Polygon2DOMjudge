import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest
import yaml

from p2d import DomjudgeOptions, GlobalConfig, ProcessError
from test.helpers.packages import export


@pytest.mark.parametrize("legacy", [False, True], ids=["2025-09", "legacy"])
@pytest.mark.parametrize(
    ("passes", "interactive", "mode"),
    [
        pytest.param(1, True, "interactive", id="interactive"),
        pytest.param(2, False, "multi-pass", id="multi-pass"),
        pytest.param(2, True, "interactive multi-pass", id="interactive-multi-pass"),
    ],
)
@pytest.mark.parametrize("hide_sample", [None, False, True], ids=["default", "visible", "hidden"])
def test_interaction_modes(
    interactive_dir: Path, tmp_path: Path, legacy: bool, passes: int, interactive: bool, mode: str, hide_sample: bool | None
) -> None:
    package = interactive_dir
    tree = ET.parse(package / "problem.xml")
    statements = tree.find("statements")
    assert statements is not None
    statements.set("use-interaction-log-in-example-tests", "true")
    interaction = b"< 1\n> 2\n" if passes == 1 else b"< 1\n> 2\n---\n< 2\n> 3\n"
    hidden = passes > 1 if hide_sample is None else hide_sample
    if not hidden:
        (package / "statements/english/example.01.i").write_bytes(interaction)
    judging = tree.find("judging")
    assert judging is not None
    judging.set("run-count", str(passes))
    interactor = tree.find("assets/interactor")
    assert interactor is not None
    if passes > 1 and interactive:
        runs = ET.SubElement(interactor, "runs")
        ET.SubElement(runs, "run")
        ET.SubElement(runs, "run")
    tree.write(package / "problem.xml", encoding="utf-8")
    output = tmp_path / "interaction.zip"
    files = export(package, output, DomjudgeOptions(legacy=legacy, auto_detect_std_checker=True, hide_sample=hide_sample))
    metadata = yaml.safe_load(files["problem.yaml"])
    if legacy:
        assert metadata["validation"] == f"custom {mode}"
        validator = "output_validators/interactor"
    else:
        assert metadata["type"] == mode
        assert "validation" not in metadata
        validator = "output_validator"
    assert f"{validator}/interactor.cpp" in files
    assert f"{validator}/testlib.h" in files
    group = "secret" if hidden else "sample"
    for extension, original in (("in", "01"), ("ans", "01.a")):
        assert files[f"data/{group}/01.{extension}"] == (package / "tests" / original).read_bytes()
    if hidden:
        assert not any(name.startswith("data/sample/") or name.endswith(".interaction") for name in files)
    else:
        assert files["data/sample/01.interaction"] == interaction
    if passes > 1:
        assert metadata["limits"]["validation_passes"] == passes
        assert b"-DDOMJUDGE" in files[f"{validator}/build"]
        with zipfile.ZipFile(output) as archive:
            assert (archive.getinfo(f"{validator}/build").external_attr >> 16) & 0o111
    else:
        assert "validation_passes" not in metadata["limits"]


@pytest.mark.parametrize("legacy", [False, True], ids=["2025-09", "legacy"])
@pytest.mark.parametrize("hide_sample", [False, True], ids=["visible", "hidden"])
@pytest.mark.parametrize("keep_sample", [None, (1,)], ids=["default-output", "keep-output"])
@pytest.mark.parametrize("attribute", [None, "false", "true"], ids=["absent", "disabled", "enabled"])
def test_interaction_samples(
    interactive_dir: Path,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    legacy: bool,
    hide_sample: bool,
    keep_sample: tuple[int, ...] | None,
    attribute: str | None,
) -> None:
    tree = ET.parse(interactive_dir / "problem.xml")
    statements = tree.find("statements")
    assert statements is not None
    if attribute is not None:
        statements.set("use-interaction-log-in-example-tests", attribute)
    tree.write(interactive_dir / "problem.xml", encoding="utf-8")
    statement_dir = interactive_dir / "statements/english"
    (statement_dir / "example.01").write_bytes(b"statement input\n")
    (statement_dir / "example.01.a").write_bytes(b"statement output\n")
    interaction = b"< 1\r\n> 2\r\n< done"
    (statement_dir / "example.01.i").write_bytes(interaction)

    files = export(
        interactive_dir,
        tmp_path / "samples.zip",
        DomjudgeOptions(legacy=legacy, hide_sample=hide_sample, keep_sample=keep_sample),
    )
    group = "secret" if hide_sample else "sample"
    assert files[f"data/{group}/01.in"] == (interactive_dir / "tests/01").read_bytes()
    assert files[f"data/{group}/01.ans"] == (interactive_dir / "tests/01.a").read_bytes()
    logs = {name: content for name, content in files.items() if name.endswith(".interaction")}
    assert logs == ({"data/sample/01.interaction": interaction} if attribute == "true" and not hide_sample else {})
    assert ("data/sample/01.in" in files) == (not hide_sample)
    assert ("data/secret/01.in" in files) == hide_sample
    assert "data/secret/02.in" in files
    if keep_sample is not None:
        assert "keep_sample will be ignored" in caplog.text
    assert "is different from the sample" not in caplog.text


@pytest.fixture
def missing_interaction_log_dir(interactive_dir: Path) -> Path:
    tree = ET.parse(interactive_dir / "problem.xml")
    statements = tree.find("statements")
    assert statements is not None
    statements.set("use-interaction-log-in-example-tests", "true")
    tree.write(interactive_dir / "problem.xml", encoding="utf-8")
    return interactive_dir


@pytest.mark.parametrize("legacy", [False, True], ids=["2025-09", "legacy"])
def test_missing_interaction_log(missing_interaction_log_dir: Path, tmp_path: Path, legacy: bool) -> None:
    output = tmp_path / "missing.zip"
    with pytest.raises(ProcessError) as exc:
        export(missing_interaction_log_dir, output, DomjudgeOptions(legacy=legacy))
    expected_path = missing_interaction_log_dir / "statements/english/example.01.i"
    assert str(exc.value) == f"Sample interaction log is missing: {expected_path}"
    assert isinstance(exc.value.__cause__, FileNotFoundError)
    assert Path(exc.value.__cause__.filename) == expected_path
    assert not output.exists()


@pytest.mark.parametrize("legacy", [False, True], ids=["2025-09", "legacy"])
def test_hidden_samples_do_not_require_interaction_log(
    missing_interaction_log_dir: Path, tmp_path: Path, legacy: bool
) -> None:
    files = export(missing_interaction_log_dir, tmp_path / "hidden.zip", DomjudgeOptions(legacy=legacy, hide_sample=True))
    assert not any(name.startswith("data/sample/") or name.endswith(".interaction") for name in files)
    assert files["data/secret/01.in"] == (missing_interaction_log_dir / "tests/01").read_bytes()
    assert files["data/secret/01.ans"] == (missing_interaction_log_dir / "tests/01.a").read_bytes()


@pytest.mark.parametrize("legacy", [False, True], ids=["2025-09", "legacy"])
def test_interaction_log_language_and_paths(interactive_dir: Path, tmp_path: Path, legacy: bool) -> None:
    tree = ET.parse(interactive_dir / "problem.xml")
    names = tree.find("names")
    statements = tree.find("statements")
    assert names is not None and statements is not None
    ET.SubElement(names, "name", {"language": "chinese", "value": "猜数组"})
    statements.set("use-interaction-log-in-example-tests", "true")
    tests = tree.findall("judging/testset/tests/test")
    tests[2].set("sample", "true")
    tree.write(interactive_dir / "problem.xml", encoding="utf-8")
    chinese = interactive_dir / "statements/chinese"
    chinese.mkdir()
    for idx in (1, 3):
        (chinese / f"example{idx:02d}.i").write_bytes(f"< {idx}\n> 答案\n".encode())
        (interactive_dir / f"statements/english/example{idx:02d}.i").write_bytes(b"wrong language\n")

    config = GlobalConfig.model_validate(
        {"language_preference": ["chinese"], "example_path_pattern": {"input": "example%02d", "output": "example%02d.a"}}
    )
    files = export(interactive_dir, tmp_path / "localized.zip", DomjudgeOptions(legacy=legacy), config)
    assert {name for name in files if name.endswith(".interaction")} == {
        "data/sample/01.interaction",
        "data/sample/03.interaction",
    }
    for idx in (1, 3):
        assert files[f"data/sample/{idx:02d}.interaction"] == (chinese / f"example{idx:02d}.i").read_bytes()
        assert files[f"data/sample/{idx:02d}.in"] == (interactive_dir / f"tests/{idx:02d}").read_bytes()
        assert files[f"data/sample/{idx:02d}.ans"] == (interactive_dir / f"tests/{idx:02d}.a").read_bytes()
    assert "data/secret/02.in" in files


def test_interaction_attribute_without_interactor(polygon_dir: Path, tmp_path: Path) -> None:
    tree = ET.parse(polygon_dir / "problem.xml")
    statements = tree.find("statements")
    assert statements is not None
    statements.set("use-interaction-log-in-example-tests", "true")
    tree.write(polygon_dir / "problem.xml", encoding="utf-8")
    (polygon_dir / "statements/english/example.01.a").write_bytes(b"statement output\n")

    files = export(polygon_dir, tmp_path / "normal.zip")
    assert files["data/sample/01.ans"] == b"statement output\n"
    assert not any(name.endswith(".interaction") for name in files)


def test_interactive_without_statements(interactive_dir: Path, tmp_path: Path) -> None:
    tree = ET.parse(interactive_dir / "problem.xml")
    statements = tree.find("statements")
    assert statements is not None
    tree.getroot().remove(statements)
    tree.write(interactive_dir / "problem.xml", encoding="utf-8")

    files = export(interactive_dir, tmp_path / "no-statements.zip")
    assert files["data/sample/01.in"] == (interactive_dir / "tests/01").read_bytes()
    assert files["data/sample/01.ans"] == (interactive_dir / "tests/01.a").read_bytes()
    assert not any(name.endswith(".interaction") for name in files)
