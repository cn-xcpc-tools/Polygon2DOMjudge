"""Test data loading utilities with type safety and validation."""

from contextlib import nullcontext
from functools import partial
from pathlib import Path
from typing import Any, Callable, Generator, Optional, Type, TypeAlias, cast

import pytest
import yaml
from _pytest.mark import ParameterSet
from _pytest.python_api import RaisesContext
from pydantic import ValidationError

from . import assertions
from .models import Assertion, RaiseExpectation, TestData
from p2d import ProcessError

ExceptionContext: TypeAlias = nullcontext[None] | RaisesContext[BaseException]


class DataLoader:
    """Handles loading and validation of test data."""

    def __init__(self) -> None:
        """Initialize the data loader with validated test data."""
        self._test_data = self._load_test_data()

    def _load_test_data(self) -> TestData:
        """Load and validate test data from YAML file."""
        yaml_path = Path(__file__).parent.parent / "test_data" / "data.yaml"
        try:
            raw_data = yaml.safe_load(yaml_path.read_text())
            return TestData(**raw_data)
        except ValidationError as e:
            raise ValueError(f"Invalid test data format in {yaml_path}: {e}") from e
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse YAML file {yaml_path}: {e}") from e

    def get_assertion_function(self, assertion_name: str) -> Callable[..., None]:
        """Get assertion function by name with type checking."""
        try:
            func = getattr(assertions, f"assert_{assertion_name}")
            if not callable(func):
                raise ValueError(f"Assertion {assertion_name} is not callable")
            return cast(Callable[..., None], func)
        except AttributeError as e:
            raise ValueError(f"Assertion {assertion_name} not found in assertions module") from e

    def create_composite_assertion(self, assertions_config: list[str | Assertion]) -> Callable[..., None]:
        """Create a composite assertion function from multiple assertions."""
        if not assertions_config:
            return lambda *args, **kwargs: None

        assertion_funcs = []
        for assertion in assertions_config:
            if isinstance(assertion, str):
                assertion_funcs.append(self.get_assertion_function(assertion))
            elif isinstance(assertion, Assertion):
                func = self.get_assertion_function(assertion.type)
                assertion_funcs.append(partial(func, **assertion.args))
            else:
                raise ValueError(f"Invalid assertion configuration: {assertion}")

        def composite_assertion(*args: Any, **kwargs: Any) -> None:
            for func in assertion_funcs:
                func(*args, **kwargs)

        return composite_assertion

    def get_exception_context(self, error_config: Optional[RaiseExpectation]) -> ExceptionContext:
        """Get pytest exception context for test cases."""
        if error_config is None:
            return nullcontext()

        error_types: dict[str, Type[BaseException]] = {
            "ProcessError": ProcessError,
            "FileNotFoundError": FileNotFoundError,
            "ValueError": ValueError,
            "FileExistsError": FileExistsError,
            "SystemExit": SystemExit,
        }

        error_type = error_types.get(error_config.type, BaseException)
        return pytest.raises(error_type, match=error_config.match)

    def load_cli_test_data(self) -> Generator[ParameterSet, None, None]:
        """Load CLI test data with validation."""
        for name, test_case in self._test_data.cli.items():
            if name.startswith("__"):
                continue
            yield pytest.param(
                test_case.input,
                test_case.args,
                test_case.user_input,
                self.create_composite_assertion(test_case.assertions or []),
                test_case.exitcode,
                id=name,
            )

    def load_api_test_data(self) -> Generator[ParameterSet, None, None]:
        """Load API test data with validation."""
        for name, test_case in self._test_data.api.items():
            if name.startswith("__"):
                continue

            yield pytest.param(
                test_case.input,
                test_case.global_config,
                test_case.kwargs,
                self.create_composite_assertion(test_case.assertions or []),
                self.get_exception_context(test_case.raise_),
                id=name,
            )


_data_loader = DataLoader()

load_cli_test_data = _data_loader.load_cli_test_data
load_api_test_data = _data_loader.load_api_test_data
