import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

from p2d import DomjudgeOptions, GlobalConfig, ProcessError
from test.helpers.packages import export


@pytest.mark.parametrize(
    ("language", "expected_name"),
    [
        pytest.param("english", "Little H And Reboot", id="english"),
        pytest.param("chinese", {"zh": "小 H 的重启"}, id="chinese"),
        pytest.param("russian", {"ru": "Задача"}, id="russian"),
    ],
)
def test_statements_and_attachments(
    polygon_dir: Path, tmp_path: Path, language: str, expected_name: str | dict[str, str]
) -> None:
    tree = ET.parse(polygon_dir / "problem.xml")
    if language == "russian":
        names = tree.find("names")
        assert names is not None
        ET.SubElement(names, "name", {"language": language, "value": "Задача"})
        statements = tree.find("statements")
        assert statements is not None
        ET.SubElement(statements, "statement", {"language": language, "type": "application/pdf", "path": "russian.pdf"})
        (polygon_dir / "russian.pdf").write_bytes(b"%PDF-1.0\n")
    files_node = tree.find("files")
    assert files_node is not None
    attachments = ET.SubElement(files_node, "attachments")
    ET.SubElement(attachments, "file", {"path": "tool.py"})
    (polygon_dir / "tool.py").write_bytes(b"print('tool')\n")
    tree.write(polygon_dir / "problem.xml", encoding="utf-8")
    files = export(
        polygon_dir,
        tmp_path / "resources.zip",
        DomjudgeOptions(with_statement=True, with_attachments=True, hide_sample=True),
        GlobalConfig(language_preference=[language]),
    )
    assert yaml.safe_load(files["problem.yaml"])["name"] == expected_name
    assert files["problem_statement/problem.pdf"].startswith(b"%PDF")
    assert files["attachments/tool.py"] == b"print('tool')\n"


def test_unknown_language(polygon_dir: Path, tmp_path: Path) -> None:
    tree = ET.parse(polygon_dir / "problem.xml")
    names = tree.find("names")
    assert names is not None
    names.clear()
    ET.SubElement(names, "name", {"language": "unknown", "value": "Example"})
    tree.write(polygon_dir / "problem.xml", encoding="utf-8")
    output = tmp_path / "language.zip"
    with pytest.raises(ProcessError, match="Unsupported statement language"):
        export(polygon_dir, output)
    assert not output.exists()
