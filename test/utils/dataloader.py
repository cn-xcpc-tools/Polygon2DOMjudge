import yaml
import pytest
from pathlib import Path

from contextlib import nullcontext as does_not_raise


from . import validator

with open(Path(__file__).parent.parent / 'test_data' / 'data.yaml', 'r') as f:
    _data = yaml.safe_load(f)


def _get_validator(validator_data):
    if validator_data is None:
        return None
    return getattr(validator, validator_data['type'])(**validator_data['args'])


def _get_raises(raise_data):
    if raise_data is None:
        return does_not_raise()

    error_type = dict(
        FileNotFoundError=FileNotFoundError,
        ValueError=ValueError,
        FileExistsError=FileExistsError,
        SystemExit=SystemExit,
    ).get(raise_data['type'], Exception)
    return pytest.raises(error_type, match=raise_data['match'])


def load_cli_test_data():
    for name, test_case in _data['cli'].items():
        if name.startswith('__'):
            continue
        yield pytest.param(
            test_case['input'],                                 # package_name
            test_case['args'] + [test_case['package']],         # args
            test_case['extract'],                               # extract
            _get_validator(test_case.get('validator', None)),   # validator
            _get_raises(test_case.get('raise', None)),          # expectation
            id=name,
        )


def load_api_test_data():
    for name, test_case in _data['api'].items():
        if name.startswith('__'):
            continue
        yield pytest.param(
            test_case['input'],                                 # package_name
            test_case['args'],                                  # args
            _get_validator(test_case.get('validator', None)),   # validator
            _get_raises(test_case.get('raise', None)),          # expectation
            id=name
        )
