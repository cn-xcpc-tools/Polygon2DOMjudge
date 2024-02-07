from typing import TypedDict, Dict, List, Literal, Sequence

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

Tag = Dict[_Tag, _Result]

Flag = Dict[str, List[str]]

ValidatorFlags = Sequence[str]


class ExamplePathPattern(TypedDict):
    input: str
    output: str


class Config(TypedDict):
    language_preference: List[str]
    flag: Flag
    tag: Tag
    example_path_pattern: ExamplePathPattern
