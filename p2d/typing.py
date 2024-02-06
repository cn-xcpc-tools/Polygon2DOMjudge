from typing import TypedDict, Dict, Iterable, List, Literal, Union

_Tag = Literal[
    'MAIN',
    'ACCEPTED',
    'WRONG_ANSWER',
    'TIME_LIMIT_EXCEEDED',
    'TIME_LIMIT_EXCEEDED_OR_ACCEPTED',
    'TIME_LIMIT_EXCEEDED_OR_MEMORY_LIMIT_EXCEED',
    'MEMORY_LIMIT_EXCEEDED',
    'REJECTED',
    'FAILED'
]

_Result = Literal[
    'accepted',
    'wrong_answer',
    'time_limit_exceeded',
    # 'memory_limit_exceeded',   # not used in domjudge
    'output_limit_exceeded',
    'runtime_error',
]

_ValidatorFlag = Union[Literal[
    'case_insensitive',
    'space_change_sensitive',
    'float_tolerance',
    'float_relative_tolerance',
    'float_absolute_tolerance',
], str]

Tag = Dict[_Tag, _Result]

Flag = Dict[str, List[_ValidatorFlag]]

ValidatorFlags = Iterable[_ValidatorFlag]


class ExamplePathPattern(TypedDict):
    input: str
    output: str


class Config(TypedDict):
    flag: Flag
    tag: Tag
    example_path_pattern: ExamplePathPattern
