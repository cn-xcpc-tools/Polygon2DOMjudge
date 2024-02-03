import yaml


class DOMjudgePackageValidator():
    def __init__(self, expect_ini, expect_yaml):
        self.expect_domjudge_problem_ini = expect_ini
        self.expect_problem_yaml = expect_yaml

    def _check_domjudge_problem_ini(self, package_dir):
        with open(package_dir / 'domjudge-problem.ini', 'r') as f:
            actual = f.read()
            expect = self.expect_domjudge_problem_ini
            assert actual == expect, f'actual: {actual}, expect: {expect}'

    def _check_problem_yaml(self, package_dir):
        with open(package_dir / 'problem.yaml', 'r') as f:
            actual = yaml.safe_load(f.read())
            expect = self.expect_problem_yaml
            assert actual == expect, f'actual: {actual}, expect: {expect}'

    def validate(self, package_dir):
        assert (package_dir / 'domjudge-problem.ini').is_file()
        assert (package_dir / 'problem.yaml').is_file()
        assert (package_dir / 'data').is_dir()
        assert (package_dir / 'submissions').is_dir()
        self._check_domjudge_problem_ini(package_dir)
        self._check_problem_yaml(package_dir)

    def __call__(self, package_dir):
        return self.validate(package_dir)


class NormalValidator(DOMjudgePackageValidator):
    def validate(self, package_dir):
        super().validate(package_dir)

        # make sure that sample data are copied
        assert (package_dir / 'data' / 'sample' / '01.in').is_file()
        assert (package_dir / 'data' / 'sample' / '01.ans').is_file()

        # make sure std.cpp is copied to correct solution directory
        assert (package_dir / 'submissions' / 'accepted' / 'std.cpp').is_file()


class AutoValidationValidator(DOMjudgePackageValidator):
    def validate(self, package_dir):
        super().validate(package_dir)

        # make sure that no checker and testlib.h are copied because of std.rcmp4 is found
        assert not (package_dir / 'output_validator' / 'testlib.h').is_file()
        assert not (package_dir / 'output_validator' / 'checker.cpp').is_file()


class InteractionValidator(DOMjudgePackageValidator):
    def validate(self, package_dir):
        super().validate(package_dir)

        # interaction problem does not have sample data for download
        assert not any((package_dir / 'data' / 'sample').iterdir())

        # make sure that interactor and testlib.h are copied
        assert (package_dir / 'output_validators' / 'interactor' / 'testlib.h').is_file()
        assert (package_dir / 'output_validators' / 'interactor' / 'interactor.cpp').is_file()


__all__ = ['DOMjudgePackageValidator', 'NormalValidator', 'AutoValidationValidator', 'InteractionValidator']
