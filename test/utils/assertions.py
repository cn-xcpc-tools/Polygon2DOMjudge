import yaml


def assert_data_dir(package_dir):
    assert (package_dir / 'data').is_dir()


def assert_submissions_dir(package_dir):
    assert (package_dir / 'submissions').is_dir()


def assert_domjudge_problem_ini(package_dir, expect):
    assert (package_dir / 'domjudge-problem.ini').is_file()
    with open(package_dir / 'domjudge-problem.ini', 'r') as f:
        actual = f.read()
        assert actual == expect, f'actual: {actual}, expect: {expect}'


def assert_problem_yaml(package_dir, expect):
    assert (package_dir / 'problem.yaml').is_file()
    with open(package_dir / 'problem.yaml', 'r', encoding='utf-8') as f:
        actual = yaml.safe_load(f.read())
        assert actual == expect, f'actual: {actual}, expect: {expect}'


def assert_file(package_dir, file, expect=None):
    assert (package_dir / file).is_file()
    if expect is None:
        return
    with open(package_dir / file, 'r') as f:
        actual = f.read()
        assert actual == expect, f'actual: {actual}, expect: {expect}'


def assert_no_file(package_dir, file):
    assert not (package_dir / file).is_file()


def assert_sample_data(package_dir, expect=('01.in', '01.ans')):
    assert (package_dir / 'data' / 'sample').is_dir()
    for file in expect:
        assert (package_dir / 'data' / 'sample' / file).is_file()


def assert_no_sample_data(package_dir):
    assert not any((package_dir / 'data' / 'sample').iterdir())


def assert_secret_data(package_dir):
    assert any((package_dir / 'data' / 'secret').iterdir())


def assert_submission(package_dir, result, name):
    assert (package_dir / 'submissions' / result / name).is_file()


def assert_no_checker_and_testlib(package_dir):
    assert not (package_dir / 'output_validators' / 'checker / testlib.h').is_file()
    assert not (package_dir / 'output_validators' / 'checker / checker.cpp').is_file()


def assert_checker_and_testlib(package_dir):

    assert (package_dir / 'output_validators' / 'checker' / 'testlib.h').is_file()
    assert (package_dir / 'output_validators' / 'checker' / 'checker.cpp').is_file()


def assert_interactor_and_testlib(package_dir):
    assert (package_dir / 'output_validators' / 'interactor' / 'testlib.h').is_file()
    assert (package_dir / 'output_validators' / 'interactor' / 'interactor.cpp').is_file()


def assert_magic_string(package_dir, result, name, magic_string):
    assert_submission(package_dir, result, name)
    with open(package_dir / 'submissions' / result / name, 'r') as f:
        assert magic_string in f.read()
