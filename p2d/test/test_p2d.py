import tempfile
from path import Path
from p2d import __version__
from p2d import Polygon2DOMjudge


def test_version():
    assert len(__version__) > 0


def test_p2d():
    package_dir = Path(__file__).parent / "test_data" / "example"
    output_dir = Path(__file__).parent / "test_output"
    output_file = output_dir / "example"
    with tempfile.TemporaryDirectory(prefix="p2d-domjudge-test") as temp_dir:
        p = Polygon2DOMjudge(package_dir, temp_dir, output_file)
        p.process()
    assert (output_dir / "example.zip").exists()
