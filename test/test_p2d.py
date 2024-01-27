import os
import shutil
import zipfile
import tempfile
import yaml
from pathlib import Path

from p2d import __version__
from p2d import Polygon2DOMjudge


def test_version():
    assert len(__version__) > 0


def test_p2d():
    test_data_dir = Path(__file__).parent / "test_data"
    test_output_dir = Path(__file__).parent / "test_output"
    if os.path.exists(test_output_dir):
        shutil.rmtree(test_output_dir)
    os.mkdir(test_output_dir)

    polygon_package_zip_dir = test_data_dir / "little-h-reboot-7$linux.zip"
    target_polygon_package_zip_dir = test_output_dir / "example-polygon.zip"
    package_dir = test_output_dir / "example-polygon"
    shutil.copyfile(polygon_package_zip_dir, target_polygon_package_zip_dir)
    with zipfile.ZipFile(target_polygon_package_zip_dir, 'r') as zip_ref:
        zip_ref.extractall(package_dir)

    output_file = test_output_dir / "example-domjudge"
    with tempfile.TemporaryDirectory(prefix="p2d-domjudge-test") as temp_dir:
        p = Polygon2DOMjudge(package_dir, temp_dir, output_file, "A", "#FF0000")
        p.process()

    output_dir = test_output_dir / "example-domjudge"
    assert (test_output_dir / "example-domjudge.zip").is_file()
    with zipfile.ZipFile(test_output_dir / "example-domjudge.zip", 'r') as zip_ref:
        zip_ref.extractall(output_dir)

    assert (output_dir / "domjudge-problem.ini").is_file()
    assert (output_dir / "problem.yaml").is_file()

    with open(output_dir / "domjudge-problem.ini", "r") as f:
        assert f.read() == "short-name = A\ntimelimit = 5.0\ncolor = #FF0000\n"

    with open(output_dir / "problem.yaml", "r") as f:
        assert yaml.safe_load(f.read()) == {
            "limits": {
                "memory": 256
            },
            "name": "Little H And Reboot",
            "validation": "custom"
        }
