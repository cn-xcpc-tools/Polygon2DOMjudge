from typing import Any, Optional
from pydantic import BaseModel, Field

from p2d import GlobalConfig, Options


class Assertion(BaseModel):
    """Model for assertion arguments."""

    type: str
    args: dict[str, Any]


class RaiseExpectation(BaseModel):
    """Model for expected exceptions."""

    type: str
    match: str


class BaseTestCase(BaseModel):
    """Base model for test cases."""

    input: str
    assertions: Optional[list[str | Assertion]] = None

    model_config = {
        "extra": "allow",
    }


class APITestCase(BaseTestCase):
    """Model for API test cases."""

    kwargs: Options
    global_config: GlobalConfig = GlobalConfig()
    raise_: Optional[RaiseExpectation] = Field(None, alias="raise")


class CLITestCase(BaseTestCase):
    """Model for CLI test cases."""

    args: list[str]
    user_input: Optional[str] = None
    exitcode: int = 0
    package: Optional[str] = None


class TestData(BaseModel):
    """Root model for test data."""

    cli: dict[str, CLITestCase]
    api: dict[str, APITestCase]

    model_config = {
        "extra": "allow",
    }
