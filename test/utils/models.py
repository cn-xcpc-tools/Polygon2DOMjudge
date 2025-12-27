from typing import Any

from pydantic import BaseModel, Field

from p2d import GlobalConfig
from p2d.p2d import ConvertOptions


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
    assertions: list[str | Assertion] | None = None

    model_config = {
        "extra": "allow",
    }


class APITestCase(BaseTestCase):
    """Model for API test cases."""

    kwargs: ConvertOptions = Field(default_factory=ConvertOptions)
    global_config: GlobalConfig = Field(default_factory=GlobalConfig)
    raise_: RaiseExpectation | None = Field(None, alias="raise")


class CLITestCase(BaseTestCase):
    """Model for CLI test cases."""

    args: list[str]
    user_input: str | None = None
    exitcode: int = 0
    package: str | None = None


class TestData(BaseModel):
    """Root model for test data."""

    cli: dict[str, CLITestCase]
    api: dict[str, APITestCase]

    model_config = {
        "extra": "allow",
    }
