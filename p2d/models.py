from typing import Literal, TypeAlias

from pydantic import BaseModel

Result: TypeAlias = Literal[
    "accepted",
    "wrong_answer",
    "time_limit_exceeded",
    # 'memory_limit_exceeded',   # not used in domjudge
    "output_limit_exceeded",
    "run_time_error",
]


class ExamplePathPattern(BaseModel):
    input: str
    output: str

    model_config = {
        "frozen": True,
    }


class GlobalConfig(BaseModel):
    language_preference: list[str] = ["english", "russian", "chinese"]
    flag: dict[str, str] = {
        "fcmp.cpp": "case_sensitive space_change_sensitive",
        "lcmp.cpp": "case_sensitive",
        "rcmp4.cpp": "float_tolerance 1e-4",
        "rcmp6.cpp": "float_tolerance 1e-6",
        "rcmp9.cpp": "float_tolerance 1e-9",
        "wcmp.cpp": "case_sensitive",
    }
    tag: dict[str, list[Result]] = {
        "main": ["accepted"],
        "accepted": ["accepted"],
        "wrong-answer": ["wrong_answer"],
        "presentation-error": ["wrong_answer"],
        "time-limit-exceeded": ["time_limit_exceeded"],
        "time-limit-exceeded-or-accepted": ["time_limit_exceeded", "accepted"],
        "time-limit-exceeded-or-memory-limit-exceeded": [
            "time_limit_exceeded",
            "run_time_error",
        ],
        "memory-limit-exceeded": ["run_time_error"],
        "rejected": ["wrong_answer", "time_limit_exceeded", "run_time_error"],
        "failed": ["wrong_answer", "time_limit_exceeded", "run_time_error"],
    }
    example_path_pattern: ExamplePathPattern = ExamplePathPattern(input="example.%02d", output="example.%02d.a")
    comment_str: dict[str, str] = {
        "c": "//",
        "cpp": "//",
        "java": "//",
        "python": "#",
        "kotlin": "//",
    }

    model_config = {
        "frozen": True,
    }
