import shutil
import zipfile

import pytest

from pathlib import Path

from .utils.dataloader import load_cli_test_data, load_api_test_data


def test_version():
    from p2d import __version__
    assert len(__version__.split('.')) == 3


def test_cli_version(capsys):
    from p2d import __version__
    from p2d.cli import main
    with pytest.raises(SystemExit):
        main(['--version'])
    captured = capsys.readouterr()
    assert captured.out.strip() == __version__


@pytest.mark.parametrize('package_name, args, validator, expectation', load_api_test_data())
def test_api(tmp_path, monkeypatch, package_name, args, validator, expectation):
    import tempfile
    monkeypatch.chdir(tmp_path)
    test_data_dir = Path(__file__).parent / 'test_data'
    polygon_package_dir = tmp_path / 'example-polygon-dir'
    domjudge_package_dir = tmp_path / 'example-domjudge-dir'
    polygon_package = tmp_path / 'example-polygon.zip'
    domjudge_package = tmp_path / 'example-domjudge.zip'
    domjudge_package_without_ext = tmp_path / 'example-domjudge'

    shutil.copyfile(test_data_dir / package_name, polygon_package)
    with zipfile.ZipFile(polygon_package, 'r') as zip_ref:
        zip_ref.extractall(polygon_package_dir)

    from p2d import Polygon2DOMjudge

    with expectation:
        with tempfile.TemporaryDirectory('p2d-domjudge-') as tmpdir:
            p = Polygon2DOMjudge(polygon_package_dir, tmpdir, domjudge_package_without_ext, **args)
            p.process()

        assert domjudge_package.is_file()

        # Extract the output zip file for further assertion
        with zipfile.ZipFile(domjudge_package, 'r') as zip_ref:
            zip_ref.extractall(domjudge_package_dir)

        validator(domjudge_package_dir)


@pytest.mark.parametrize('package_name, args, extract, validator, expectation', load_cli_test_data())
def test_cli(tmp_path, monkeypatch, package_name, args, extract, validator, expectation):
    monkeypatch.chdir(tmp_path)
    test_data_dir = Path(__file__).parent / 'test_data'
    polygon_package_dir = tmp_path / 'example-polygon-dir'
    domjudge_package_dir = tmp_path / 'example-domjudge-dir'
    polygon_package = tmp_path / 'example-polygon.zip'
    domjudge_package = tmp_path / 'example-domjudge.zip'

    shutil.copyfile(test_data_dir / package_name, polygon_package)
    if extract:
        with zipfile.ZipFile(polygon_package, 'r') as zip_ref:
            zip_ref.extractall(polygon_package_dir)

    from p2d.cli import main

    with expectation:
        assert main(args, raise_exception=True) == 0

        assert domjudge_package.is_file()

        # Extract the output zip file for further assertion
        with zipfile.ZipFile(domjudge_package, 'r') as zip_ref:
            zip_ref.extractall(domjudge_package_dir)

        validator(domjudge_package_dir)
