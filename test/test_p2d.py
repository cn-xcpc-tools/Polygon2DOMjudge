import tempfile
from path import Path
from p2d import __version__
from p2d import Polygon2DOMjudge
import os
import shutil
import zipfile


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
        p = Polygon2DOMjudge(package_dir, temp_dir, output_file)
        p.process()

    assert (test_output_dir / "example-domjudge.zip").exists()
