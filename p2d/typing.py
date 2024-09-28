from typing import Dict, List, Literal, TypedDict


Result = Literal[
    'accepted',
    'wrong_answer',
    'time_limit_exceeded',
    # 'memory_limit_exceeded',   # not used in domjudge
    'output_limit_exceeded',
    'runtime_error'
]

TagMapping = Dict[str, List[Result]]

FlagMapping = Dict[str, str]


class ExamplePathPattern(TypedDict):
    input: str
    output: str


class Config(TypedDict):
    language_preference: List[str]
    flag: FlagMapping
    tag: TagMapping
    example_path_pattern: ExamplePathPattern
    comment_str: Dict[str, str]
