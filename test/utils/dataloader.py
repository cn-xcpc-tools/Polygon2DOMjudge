from contextlib import nullcontext as does_not_raise
from functools import partial
from pathlib import Path

import pytest
import yaml

from . import assertions

with open(Path(__file__).parent.parent / 'test_data' / 'data.yaml', 'r') as f:
    _data = yaml.safe_load(f)


def __get_all_assertions(data):
    for assertion in data:
        if isinstance(assertion, str):
            yield getattr(assertions, f'assert_{assertion}')
        else:
            yield partial(getattr(assertions, f'assert_{assertion["type"]}'), **assertion.get('args', {}))


def _get_asserts(data):

    def func(*args, **kwargs):
        for assertion in __get_all_assertions(data):
            assertion(*args, **kwargs)

    return func


def _get_raises(data):
    if data is None:
        return does_not_raise()

    error_type = dict(
        FileNotFoundError=FileNotFoundError,
        ValueError=ValueError,
        FileExistsError=FileExistsError,
        SystemExit=SystemExit,
    ).get(data['type'], Exception)

    return pytest.raises(error_type, match=data['match'])


def load_cli_test_data():
    for name, test_case in _data['cli'].items():
        if name.startswith('__'):
            continue
        yield pytest.param(
            test_case['input'],                          # package_name
            test_case['args'],                                  # args
            _get_asserts(test_case.get('assertions', None)),    # asserts
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
            _get_asserts(test_case.get('assertions', None)),    # asserts
            _get_raises(test_case.get('raise', None)),          # expectation
            id=name,
        )
