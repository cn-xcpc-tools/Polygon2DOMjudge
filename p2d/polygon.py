from __future__ import annotations

import logging
import re
import xml.etree.ElementTree
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING
from xml.etree.ElementTree import Element

from .exceptions import ProcessError

if TYPE_CHECKING:  # pragma: no cover
    from _typeshed import StrPath

logger = logging.getLogger(__name__)

UNKNOWN = "unknown"


class PolygonProblem:
    """Representation of a Polygon problem loaded from problem.xml."""

    _LANGUAGE_PREFERENCE = (
        "english",
        "russian",
        "chinese",
    )

    _SHORT_NAME_FILTER = re.compile(r"[^a-zA-Z0-9-_]")

    class TestCase:
        def __init__(
            self,
            method: str,
            description: str | None = None,
            cmd: str | None = None,
            sample: bool = False,
        ) -> None:
            self.method = method
            self.description = description
            self.cmd = cmd
            self.sample = sample

        def __str__(self) -> str:
            description = self.description if self.description else ""
            cmd = f"[GEN] {self.cmd}" if self.cmd else ""
            return f"{description} {cmd}".strip()

    class Executable:
        def __init__(self, path: str, name: str = UNKNOWN) -> None:
            self.path = path
            self.name = name

        @classmethod
        def from_element(cls, ele: Element | None) -> PolygonProblem.Executable | None:
            if ele is not None and (source := ele.find("source")) is not None:
                return PolygonProblem.Executable(source.attrib["path"], ele.attrib.get("name", UNKNOWN))
            return None

    def __init__(
        self,
        problem_xml: StrPath,
        /,
        language_preference: Sequence[str] = _LANGUAGE_PREFERENCE,
        testset_name: str | None = None,
    ) -> None:
        """Initialize the problem class from problem.xml."""
        problem = xml.etree.ElementTree.parse(problem_xml).getroot()

        if not isinstance(problem, Element):
            msg = "Invalid problem.xml"
            raise ProcessError(msg)

        short_name = self._SHORT_NAME_FILTER.sub("", problem.attrib.get("short-name", ""))
        name, language = self._get_preference_name(problem.find("names"), language_preference)
        statement = self._get_statement(problem.find("statements"), language)

        judging = problem.find("judging")
        if judging is None:
            msg = "Can not find judgings in problem.xml."
            raise ProcessError(msg)
        run_count = judging.attrib.get("run-count", "1")

        testset = self._get_testset(problem, testset_name)

        if not short_name:
            msg = "Short name is invalid in problem.xml."
            raise ProcessError(msg)

        timelimit_ms = self._require_positive_int(testset.find("time-limit"), "time limit")
        memorylimit_bytes = self._require_positive_int(testset.find("memory-limit"), "memory limit")
        input_path_pattern = self._require_text(testset.find("input-path-pattern"), "input path pattern")
        answer_path_pattern = self._require_text(testset.find("answer-path-pattern"), "answer path pattern")
        run_count_value = self._parse_positive_int(run_count, "run count")

        self.short_name = short_name
        self.name = name
        self.language = language
        self.timelimit = timelimit_ms / 1000.0
        self.memorylimit = memorylimit_bytes // 1048576
        self.outputlimit = -1
        self.input_path_pattern = input_path_pattern
        self.answer_path_pattern = answer_path_pattern
        self.checker = self.Executable.from_element(problem.find("assets/checker[source]"))
        self.interactor = self.Executable.from_element(problem.find("assets/interactor[source]"))
        self.test_cases = tuple(
            self.TestCase(
                method=test.attrib["method"],
                description=test.attrib.get("description", None),
                cmd=test.attrib.get("cmd", None),
                sample=self._parse_bool_attribute(test.attrib.get("sample")),
            )
            for test in testset.findall("tests/test")
        )
        self.solutions = tuple(problem.findall("assets/solutions/solution[@tag]"))
        self.statement = statement
        self.attachments = tuple(Path(ele.attrib["path"]) for ele in problem.findall("files/attachments/file[@path]"))
        self.run_count = run_count_value

    @staticmethod
    def _get_preference_name(
        names: Element | None,
        language_preference: Sequence[str] = _LANGUAGE_PREFERENCE,
    ) -> tuple[str, str]:
        if names is None:
            msg = "Can not find names in problem.xml."
            raise ProcessError(msg)

        for lang in language_preference:
            name = names.find(f'name[@language="{lang}"]')
            if name is not None and "value" in name.attrib and "language" in name.attrib:
                return name.attrib["value"], name.attrib["language"]

        name = names.find("name")
        if name is not None and "value" in name.attrib and "language" in name.attrib:
            return name.attrib["value"], name.attrib["language"]

        msg = "Name is invalid in problem.xml."
        raise ProcessError(msg)

    @staticmethod
    def _get_testset(problem: Element, testset_name: str | None) -> Element:
        if testset_name is None:
            if t := problem.findall("judging/testset"):
                if len(t) == 1:
                    return t[0]
                msg = "Multiple testsets found in problem.xml. Please specify testset_name."
                raise ProcessError(msg)
            msg = "Can not find any testset in problem.xml."
            raise ProcessError(msg)

        if (ele := problem.find(f'judging/testset[@name="{testset_name}"]')) is None:
            logger.error("Can not find testset %s in problem.xml.", testset_name)
            msg = f"Can not find testset {testset_name} in problem.xml."
            raise ProcessError(msg)
        return ele

    @staticmethod
    def _get_statement(statements: Element | None, language: str) -> StrPath | None:
        if statements is None:
            return None

        if (statement := statements.find(f'statement[@language="{language}"][@type="application/pdf"][@path]')) is None:
            logger.warning(
                "Can not find statement in %s in problem.xml, this will skip adding statement.",
                language,
            )
            return None

        return statement.attrib["path"]

    @staticmethod
    def _require_text(element: Element | None, description: str) -> str:
        if element is None or element.text is None:
            msg = f"{description.capitalize()} is invalid in problem.xml."
            raise ProcessError(msg)
        return element.text

    @staticmethod
    def _require_positive_int(element: Element | None, description: str) -> int:
        text = PolygonProblem._require_text(element, description)
        if text.isdigit():
            return int(text)
        msg = f"{description.capitalize()} is invalid in problem.xml."
        raise ProcessError(msg)

    @staticmethod
    def _parse_positive_int(value: str | None, description: str) -> int:
        if value and value.isdigit():
            return int(value)
        msg = f"{description.capitalize()} is invalid in problem.xml."
        raise ProcessError(msg)

    @staticmethod
    def _parse_bool_attribute(value: str | None) -> bool:
        if value is None:
            return False
        return value.strip().lower() in {"true", "1", "yes"}
