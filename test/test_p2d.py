import shutil
import zipfile
import tempfile
import yaml
from pathlib import Path

from p2d import __version__
from p2d import Polygon2DOMjudge


def test_version():
    assert len(__version__) > 0


def run_p2d_with_testcase(name, test_case, *args, **kwargs):
    test_data_dir = Path(__file__).parent / 'test_data'
    test_output_dir = Path(__file__).parent / 'test_output' / name
    if test_output_dir.is_dir():
        shutil.rmtree(test_output_dir)
    test_output_dir.mkdir(parents=True, exist_ok=True)

    polygon_package_zip_dir = test_data_dir / test_case
    target_polygon_package_zip_dir = test_output_dir / 'example-polygon.zip'
    package_dir = test_output_dir / 'example-polygon'
    shutil.copyfile(polygon_package_zip_dir, target_polygon_package_zip_dir)
    with zipfile.ZipFile(target_polygon_package_zip_dir, 'r') as zip_ref:
        zip_ref.extractall(package_dir)

    output_file = test_output_dir / 'example-domjudge'
    with tempfile.TemporaryDirectory(prefix='p2d-domjudge-test') as temp_dir:
        p = Polygon2DOMjudge(package_dir, temp_dir, output_file, *args, **kwargs)
        p.process()

    output_dir = test_output_dir / 'example-domjudge'
    with zipfile.ZipFile(test_output_dir / 'example-domjudge.zip', 'r') as zip_ref:
        zip_ref.extractall(output_dir)
    return test_output_dir, output_dir


def test_normal():
    test_output_dir, output_dir = run_p2d_with_testcase('01-normal', 'little-h-reboot-7$linux.zip', 'A', '#FF0000')
    assert (test_output_dir / 'example-domjudge.zip').is_file()
    assert (output_dir / 'domjudge-problem.ini').is_file()
    assert (output_dir / 'problem.yaml').is_file()

    with open(output_dir / 'domjudge-problem.ini', 'r') as f:
        assert f.read() == 'short-name = A\ntimelimit = 5.0\ncolor = #FF0000\n'

    with open(output_dir / 'problem.yaml', 'r') as f:
        assert yaml.safe_load(f.read()) == {
            'limits': {
                'memory': 256
            },
            'name': 'Little H And Reboot',
            'validation': 'custom'
        }

    # make sure that sample data are copied
    assert (output_dir / 'data' / 'sample' / '01.in').is_file()
    assert (output_dir / 'data' / 'sample' / '01.ans').is_file()
    assert (output_dir / 'data' / 'sample' / '01.desc').is_file()

    # make sure that checker and testlib.h are copied
    assert (output_dir / 'output_validators' / 'checker' / 'testlib.h').is_file()
    assert (output_dir / 'output_validators' / 'checker' / 'checker.cpp').is_file()


def test_auto_validation():
    test_output_dir, output_dir = run_p2d_with_testcase('02-auto-validation', 'little-h-reboot-7$linux.zip', 'A', '#FF0000', validator_flags=('__auto'))
    assert (test_output_dir / 'example-domjudge.zip').is_file()
    assert (output_dir / 'domjudge-problem.ini').is_file()
    assert (output_dir / 'problem.yaml').is_file()

    with open(output_dir / 'domjudge-problem.ini', 'r') as f:
        assert f.read() == 'short-name = A\ntimelimit = 5.0\ncolor = #FF0000\n'

    with open(output_dir / 'problem.yaml', 'r') as f:
        assert yaml.safe_load(f.read()) == {
            'limits': {
                'memory': 256
            },
            'name': 'Little H And Reboot',
            'validation': 'default',
            'validator_flags': 'float_tolerance 1e-4'
        }

    # make sure that no checker and testlib.h are copied because of std::rcmp4 is found
    assert not (output_dir / 'output_validator' / 'testlib.h').is_file()
    assert not (output_dir / 'output_validator' / 'checker.cpp').is_file()


def test_interaction():
    test_output_dir, output_dir = run_p2d_with_testcase('03-interaction', 'guess-array-1$linux.zip', 'B', '#FF7F00')
    assert (test_output_dir / 'example-domjudge.zip').is_file()
    assert (output_dir / 'domjudge-problem.ini').is_file()
    assert (output_dir / 'problem.yaml').is_file()

    with open(output_dir / 'domjudge-problem.ini', 'r') as f:
        assert f.read() == 'short-name = B\ntimelimit = 1.0\ncolor = #FF7F00\n'

    with open(output_dir / 'problem.yaml', 'r') as f:
        assert yaml.safe_load(f.read()) == {
            'limits': {
                'memory': 512
            },
            'name': 'Guess The Array',
            'validation': 'custom interactive'
        }

    # interaction problem does not have sample data for download
    assert not any((output_dir / 'data' / 'sample').iterdir())

    # make sure that interactor and testlib.h are copied
    assert (output_dir / 'output_validators' / 'interactor' / 'testlib.h').is_file()
    assert (output_dir / 'output_validators' / 'interactor' / 'interactor.cpp').is_file()
