import shutil
import zipfile
from pathlib import Path

import pytest

from .utils.dataloader import load_cli_test_data, load_api_test_data


def test_version():
    from p2d import __version__
    assert len(__version__) > 0


def test_cli_version(capsys):
    from p2d import __version__
    from p2d.cli import main
    with pytest.raises(SystemExit):
        main(['--version'])
    captured = capsys.readouterr()
    assert captured.out.strip() == __version__


@pytest.mark.parametrize('extract', [True, False], ids=['dir', 'zip'])
@pytest.mark.parametrize('package_name, args, assertion, expectation', load_api_test_data())
def test_api(tmp_path, monkeypatch, package_name, extract, args, assertion, expectation):
    monkeypatch.chdir(tmp_path)
    test_data_dir = Path(__file__).parent / 'test_data'
    polygon_package_dir = tmp_path / 'example-polygon-dir'
    domjudge_package_dir = tmp_path / 'example-domjudge-dir'
    polygon_package = tmp_path / 'example-polygon.zip'
    domjudge_package = tmp_path / 'example-domjudge.zip'

    if (test_data_dir / package_name).exists():
        # there are some test cases that tests the package is not found
        # keep this error in api calling.
        shutil.copyfile(test_data_dir / package_name, polygon_package)
        if extract:
            with zipfile.ZipFile(polygon_package, 'r') as zip_ref:
                zip_ref.extractall(polygon_package_dir)

    from p2d import convert_polygon_to_domjudge

    package = polygon_package_dir if extract else polygon_package

    with expectation:
        # Skip confirmation for testing
        convert_polygon_to_domjudge(package, domjudge_package, skip_confirmation=True, **args)

        assert domjudge_package.is_file()

        # Extract the output zip file for further assertion
        with zipfile.ZipFile(domjudge_package, 'r') as zip_ref:
            zip_ref.extractall(domjudge_package_dir)

        assertion(domjudge_package_dir)


@pytest.mark.parametrize('extract', [True, False], ids=['dir', 'zip'])
@pytest.mark.parametrize('package_name, args, assertion, expectation', load_cli_test_data())
def test_cli(tmp_path, monkeypatch, package_name, args, extract, assertion, expectation):
    monkeypatch.chdir(tmp_path)
    test_data_dir = Path(__file__).parent / 'test_data'
    polygon_package_dir = tmp_path / 'example-polygon-dir'
    domjudge_package_dir = tmp_path / 'example-domjudge-dir'
    polygon_package = tmp_path / 'example-polygon.zip'
    domjudge_package = tmp_path / 'example-domjudge.zip'

    if (test_data_dir / package_name).exists():
        # there are some test cases that tests the package is not found
        # keep this error in cli calling.
        shutil.copyfile(test_data_dir / package_name, polygon_package)
        if extract:
            with zipfile.ZipFile(polygon_package, 'r') as zip_ref:
                zip_ref.extractall(polygon_package_dir)

    from p2d.cli import main

    package = polygon_package_dir if extract else polygon_package

    with expectation:
        assert main(args + [package.name]) == 0

        assert domjudge_package.is_file()

        # Extract the output zip file for further assertion
        with zipfile.ZipFile(domjudge_package, 'r') as zip_ref:
            zip_ref.extractall(domjudge_package_dir)

        assertion(domjudge_package_dir)
