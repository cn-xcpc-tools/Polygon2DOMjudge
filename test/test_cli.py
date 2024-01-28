import contextlib
import shutil
import pytest
import yaml
import zipfile

from os import chdir
from pathlib import Path

from p2d.cli import main


@contextlib.contextmanager
def working_directory(path):
    """Changes working directory and returns to previous on exit."""
    prev_cwd = Path.cwd()
    chdir(path)
    try:
        yield
    finally:
        chdir(prev_cwd)


def run_cli_with_testcase(name, test_case, use_zip, *args):
    test_data_dir = Path(__file__).parent / 'test_data'
    test_output_dir = Path(__file__).parent / 'test_output' / 'cli' / name
    if test_output_dir.is_dir():
        shutil.rmtree(test_output_dir)
    test_output_dir.mkdir(parents=True, exist_ok=True)

    polygon_package_zip = test_data_dir / test_case
    target_polygon_package_zip = test_output_dir / 'example-polygon.zip'
    package_dir = test_output_dir / 'example-polygon'
    shutil.copyfile(polygon_package_zip, target_polygon_package_zip)

    if not use_zip:
        with zipfile.ZipFile(target_polygon_package_zip, 'r') as zip_ref:
            zip_ref.extractall(package_dir)

    with working_directory(test_output_dir):
        exit_code = main(list(args))

    if exit_code != 0:
        raise RuntimeError(f'Exit code is {exit_code}')

    output_dir = test_output_dir / 'example-domjudge'
    with zipfile.ZipFile(test_output_dir / 'example-domjudge.zip', 'r') as zip_ref:
        zip_ref.extractall(output_dir)
    return test_output_dir, output_dir


def test_fail():
    args = ('--color', '#FF0000', '--code', 'A', '-o', 'example-polygon', '-y', 'example-polygon.zip')
    pytest.raises(RuntimeError, run_cli_with_testcase, '00_fail', 'little-h-reboot-7$linux.zip', True, *args)


def test_normal_zip():
    args = ('--color', '#FF0000', '--code', 'A', '-o', 'example-domjudge.zip', '-y', 'example-polygon.zip')
    test_output_dir, output_dir = run_cli_with_testcase('01_normal_zip', 'little-h-reboot-7$linux.zip', True, *args)
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

    # make sure std.cpp is copied to correct solution directory
    assert (output_dir / 'submissions' / 'accepted' / 'std.cpp').is_file()


def test_normal_dir():
    args = ('--color', '#FF0000', '--code', 'A', '-o', 'example-domjudge.zip', '-y', 'example-polygon.zip')
    test_output_dir, output_dir = run_cli_with_testcase('01_normal_dir', 'little-h-reboot-7$linux.zip', False, *args)
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

    # make sure std.cpp is copied to correct solution directory
    assert (output_dir / 'submissions' / 'accepted' / 'std.cpp').is_file()


def test_auto_validation():
    args = ('--color', '#FF0000', '--code', 'A', '-o', 'example-domjudge', '--auto', '-y', 'example-polygon.zip')
    test_output_dir, output_dir = run_cli_with_testcase('03_auto_validation', 'little-h-reboot-7$linux.zip', False, *args)
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
    args = ('--color', '#FF7F00', '--code', 'B', '-o', 'example-domjudge', '--auto', '-y', 'example-polygon.zip')
    test_output_dir, output_dir = run_cli_with_testcase('04_interaction', 'guess-array-1$linux.zip', False, *args)
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


def test_override():
    args = ('--color', '#FF0000', '--code', 'A', '-o', 'example-domjudge', '--memory-limit', '-1', '--output-limit', '64' , '-y', 'example-polygon.zip')
    test_output_dir, output_dir = run_cli_with_testcase('03_auto_validation', 'little-h-reboot-7$linux.zip', False, *args)
    assert (test_output_dir / 'example-domjudge.zip').is_file()
    assert (output_dir / 'domjudge-problem.ini').is_file()
    assert (output_dir / 'problem.yaml').is_file()

    with open(output_dir / 'domjudge-problem.ini', 'r') as f:
        assert f.read() == 'short-name = A\ntimelimit = 5.0\ncolor = #FF0000\n'

    with open(output_dir / 'problem.yaml', 'r') as f:
        assert yaml.safe_load(f.read()) == {
            'limits': {
                'output': 64
            },
            'name': 'Little H And Reboot',
            'validation': 'custom'
        }
