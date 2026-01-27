from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from p2d import DEFAULT_COLOR, ConvertOptions, DomjudgeOptions, GlobalConfig


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


class DomjudgeOptionsConfig(BaseModel):
    """Schema for DomjudgeOptions values defined in YAML."""

    color: str = DEFAULT_COLOR
    force_default_validator: bool = False
    auto_detect_std_checker: bool = False
    validator_flags: str | None = None
    hide_sample: bool = False
    keep_sample: tuple[int, ...] | list[int] | None = None
    external_id: str | None = None
    with_statement: bool = False
    with_attachments: bool = False
    memory_limit_override: int | None = None
    output_limit_override: int | None = None
    model_config = {
        "extra": "forbid",
    }

    def to_domjudge_options(self) -> DomjudgeOptions:
        keep_sample_tuple: tuple[int, ...] | None
        if self.keep_sample is None:
            keep_sample_tuple = None
        elif isinstance(self.keep_sample, tuple):
            keep_sample_tuple = self.keep_sample
        else:
            keep_sample_tuple = tuple(self.keep_sample)
        return DomjudgeOptions(
            color=self.color,
            force_default_validator=self.force_default_validator,
            auto_detect_std_checker=self.auto_detect_std_checker,
            validator_flags=self.validator_flags,
            hide_sample=self.hide_sample,
            keep_sample=keep_sample_tuple,
            external_id=self.external_id,
            with_statement=self.with_statement,
            with_attachments=self.with_attachments,
            memory_limit_override=self.memory_limit_override,
            output_limit_override=self.output_limit_override,
        )


class ConvertConfig(BaseModel):
    """Schema for ConvertOptions defined in YAML."""

    short_name: str
    testset_name: str | None = None
    options: DomjudgeOptionsConfig = Field(default_factory=DomjudgeOptionsConfig)
    model_config = {
        "extra": "forbid",
        "arbitrary_types_allowed": True,
    }

    def build(self, global_config: GlobalConfig, output_path: Path) -> tuple[str, ConvertOptions]:
        return self.short_name, ConvertOptions(
            output=output_path,
            global_config=global_config,
            options=self.options.to_domjudge_options(),
            testset_name=self.testset_name,
        )


class APITestCase(BaseTestCase):
    """Model for API test cases."""

    convert: ConvertConfig
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
