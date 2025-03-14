from __future__ import annotations

import errno
import logging
import os
import re
import shutil
import sys
import tempfile
import xml.etree.ElementTree
import zipfile
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    TypedDict,
    cast,
)
from xml.etree.ElementTree import Element

import yaml

from ._version import __version__
from .typing import Config, Result
from .utils import ensure_dir, get_normalized_lang, load_config, update_dict

if sys.version_info < (3, 11):  # pragma: no cover
    from typing_extensions import Unpack
else:  # pragma: no cover
    from typing import Unpack

if TYPE_CHECKING:
    from _typeshed import StrPath

logger = logging.getLogger(__name__)

DEFAULT_ASSET_PATH = Path(__file__).resolve().parent / "asset"
DEFAULT_TESTLIB_PATH = Path(__file__).resolve().parent / "testlib"
DEFAULT_CONFIG_FILE = Path(os.getenv("CONFIG_PATH", DEFAULT_ASSET_PATH)) / "config.toml"
DEFAULT_COLOR = "#000000"
UNKNOWN = "unknown"

TESTLIB_PATH = (Path(os.getenv("TESTLIB_PATH", DEFAULT_TESTLIB_PATH)) / "testlib.h").resolve()


class _Polygon2DOMjudgeArgs(TypedDict, total=False):
    force_default_validator: bool
    auto_detect_std_checker: bool
    validator_flags: Optional[str]
    hide_sample: bool
    keep_sample: Optional[Sequence[int]]
    testset_name: Optional[str]
    external_id: Optional[str]
    with_statement: bool
    with_attachments: bool
    config: Config


class _ProblemArgs(TypedDict, total=False):
    language_preference: Sequence[str]
    testset_name: Optional[str]


class ProcessError(RuntimeError):
    pass


class Polygon2DOMjudge:
    class Problem:
        """
        The problem class.
        """

        _LANGUAGE_PREFERENCE = (
            "english",
            "russian",
            "chinese",
        )

        _SHORT_NAME_FILTER = re.compile(r"[^a-zA-Z0-9-_]")

        class Test:
            def __init__(
                self,
                method: str,
                description: Optional[str] = None,
                cmd: Optional[str] = None,
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
            def __init__(self, path: str, name: str = UNKNOWN, **kwargs) -> None:
                self.path = path
                self.name = name

            @classmethod
            def from_element(cls, ele: Optional[Element]) -> Optional[Polygon2DOMjudge.Problem.Executable]:
                if ele is not None and (source := ele.find("source")) is not None:
                    return Polygon2DOMjudge.Problem.Executable(source.attrib["path"], ele.attrib.get("name", UNKNOWN))
                return None

        def __init__(self, problem_xml: StrPath, /, **kwargs: Unpack[_ProblemArgs]) -> None:
            """Initialize the problem class from problem.xml.

            Args:
                problem_xml (StrPath): Path to problem.xml.

            Raises:
                ProcessError: If some mandatory fields are missing or invalid.
            """

            language_preference = kwargs.get("language_preference", self._LANGUAGE_PREFERENCE)
            testset_name = kwargs.get("testset_name", None)

            problem = xml.etree.ElementTree.parse(problem_xml).getroot()

            if not isinstance(problem, Element):
                raise ProcessError("Invalid problem.xml")

            short_name = self._SHORT_NAME_FILTER.sub("", problem.attrib.get("short-name", ""))
            name, language = self._get_preference_name(problem.find("names"), language_preference)
            statement = self._get_statement(problem.find("statements"), language)

            judging = problem.find("judging")
            if judging is None:
                logger.error("Can not find judgings in problem.xml.")
                raise ProcessError("Can not find judgings in problem.xml.")
            run_count = judging.attrib.get("run-count", "1")

            testset = self._get_testset(problem, testset_name)

            timelimit = testset.find("time-limit")
            memorylimit = testset.find("memory-limit")
            input_path_pattern = testset.find("input-path-pattern")
            answer_path_pattern = testset.find("answer-path-pattern")

            if not short_name:
                logger.error("Short name is invalid in problem.xml.")
                raise ProcessError("Short name is invalid in problem.xml.")

            if timelimit is None or timelimit.text is None or not timelimit.text.isdigit():
                logger.error("Time limit is invalid in problem.xml.")
                raise ProcessError("Time limit is invalid in problem.xml.")

            if memorylimit is None or memorylimit.text is None or not memorylimit.text.isdigit():
                logger.error("Memory limit is invalid in problem.xml.")
                raise ProcessError("Memory limit is invalid in problem.xml.")

            if input_path_pattern is None or input_path_pattern.text is None:
                logger.error("Input path pattern is invalid in problem.xml.")
                raise ProcessError("Input path pattern is invalid in problem.xml.")

            if answer_path_pattern is None or answer_path_pattern.text is None:
                logger.error("Answer path pattern is invalid in problem.xml.")
                raise ProcessError("Answer path pattern is invalid in problem.xml.")

            if run_count is None or not run_count.isdigit():
                logger.error("Run count is invalid in problem.xml.")
                raise ProcessError("Run count is invalid in problem.xml.")

            self.short_name = short_name
            self.name = name
            self.language = language
            self.timelimit = int(timelimit.text) / 1000.0
            self.memorylimit = int(memorylimit.text) // 1048576
            self.outputlimit = -1
            self.input_path_pattern = input_path_pattern.text
            self.answer_path_pattern = answer_path_pattern.text
            self.checker = self.Executable.from_element(problem.find("assets/checker[source]"))
            self.interactor = self.Executable.from_element(problem.find("assets/interactor[source]"))
            self.tests = tuple(
                self.Test(
                    method=test.attrib["method"],
                    description=test.attrib.get("description", None),
                    cmd=test.attrib.get("cmd", None),
                    sample=bool(test.attrib.get("sample", False)),
                )
                for test in testset.findall("tests/test")
            )
            self.solutions = tuple(problem.findall("assets/solutions/solution[@tag]"))
            self.statement = statement
            self.attachments = tuple(Path(ele.attrib["path"]) for ele in problem.findall("files/attachments/file[@path]"))
            self.run_count = int(run_count)

        @staticmethod
        def _get_preference_name(
            names: Optional[Element],
            language_preference: Sequence[str] = _LANGUAGE_PREFERENCE,
        ) -> Tuple[str, str]:
            """Get the preference name.

            Args:
                names (Optional[Element]): names element in problem.xml.
                language_preference (Sequence[str], optional): language preference.

            Raises:
                ProcessError: If it can not find a valid name.

            Returns:
                Tuple[str, str]: The name and language.
            """
            if names is None:
                logger.error("Can not find names in problem.xml.")
                raise ProcessError("Can not find names in problem.xml.")

            for lang in language_preference:
                name = names.find(f'name[@language="{lang}"]')
                if name is not None and "value" in name.attrib and "language" in name.attrib:
                    return name.attrib["value"], name.attrib["language"]

            # if no preference language found, return the first name
            name = names.find("name")
            if name is not None and "value" in name.attrib and "language" in name.attrib:
                return name.attrib["value"], name.attrib["language"]

            logger.error("Name is invalid in problem.xml.")
            raise ProcessError("Name is invalid in problem.xml.")

        @staticmethod
        def _get_testset(problem: Element, testset_name: Optional[str]) -> Element:
            # if testset_name is not specified, use the only testset if there is only one testset
            if testset_name is None:
                if t := problem.findall("judging/testset"):
                    if len(t) == 1:
                        return t[0]
                    logger.error("Multiple testsets found in problem.xml.")
                    logger.error("Please specify the testset name in the command line.")
                    raise ProcessError("Multiple testsets found in problem.xml.")
                logger.error("Can not find any testset in problem.xml.")
                raise ProcessError("Can not find any testset in problem.xml.")

            # find testset by name
            if (ele := problem.find(f'judging/testset[@name="{testset_name}"]')) is None:
                logger.error("Can not find testset %s in problem.xml.", testset_name)
                raise ProcessError(f"Can not find testset {testset_name} in problem.xml.")
            return ele

        @staticmethod
        def _get_statement(statements: Optional[Element], language: str) -> Optional[StrPath]:
            if statements is None:
                return None

            if (statement := statements.find(f'statement[@language="{language}"][@type="application/pdf"][@path]')) is None:
                logger.warning(
                    "Can not find statement in %s in problem.xml, this will skip adding statement.",
                    language,
                )
                return None

            return statement.attrib["path"]

    """Polygon to DOMjudge package.
    """

    def __init__(
        self,
        package_dir: StrPath,
        temp_dir: StrPath,
        output_file: StrPath,
        short_name: str,
        /,
        color: str = DEFAULT_COLOR,
        **kwargs: Unpack[_Polygon2DOMjudgeArgs],
    ) -> None:
        """Initialize the Polygon2DOMjudge class.

        Args:
            package_dir (StrPath): The path to the polygon package directory.
            temp_dir (StrPath): The path to the temporary directory.
            output_file (StrPath): The path to the output DOMjudge package.
            short_name (str, optional): The short name of the problem.
            color (str, optional): The color of the problem.

        Raises:
            ProcessError: If some mandatory fields are missing or invalid.
        """

        force_default_validator = kwargs.get("force_default_validator", False)
        auto_detect_std_checker = kwargs.get("auto_detect_std_checker", False)
        validator_flags = kwargs.get("validator_flags", None)
        hide_sample = kwargs.get("hide_sample", False)
        keep_sample = kwargs.get("keep_sample", None)
        testset_name = kwargs.get("testset_name", None)
        external_id = kwargs.get("external_id", None)
        with_statement = kwargs.get("with_statement", False)
        with_attachments = kwargs.get("with_attachments", False)
        config = kwargs.get("config", cast(Config, load_config(DEFAULT_CONFIG_FILE)))

        if not force_default_validator and validator_flags:
            logger.warning("You are not using default validation, validator flags will be ignored.")

        self.package_dir = Path(package_dir)
        self.short_name = short_name
        self.color = color
        self.temp_dir = Path(temp_dir)
        self.output_file = Path(output_file)

        self._with_statement = with_statement
        self._with_attachments = with_attachments
        self._config = config

        logger.debug("Parse 'problem.xml':")
        if testset_name:
            logger.debug("With testset_name: %s", testset_name)
        self._problem = self.Problem(
            self.package_dir / "problem.xml",
            language_preference=self._config["language_preference"],
            testset_name=testset_name,
        )
        self.external_id = external_id if external_id else self._problem.short_name

        if force_default_validator and auto_detect_std_checker:
            logger.error("Can not use auto_detect_std_checker and force_default_validator at the same time.")
            raise ValueError("Can not use auto_detect_std_checker and force_default_validator at the same time.")

        self._hide_sample = hide_sample or self._problem.interactor is not None

        if not self._hide_sample:
            self._keep_sample = keep_sample
        else:
            logger.warning("Hide sample is enabled, all samples will be hidden, keep_sample will be ignored.")
            self._keep_sample = None

        self._use_std_checker = (
            auto_detect_std_checker
            and self._problem.checker is not None
            and self._problem.checker.name.startswith("std::")
            or force_default_validator
        )
        self._validator_flags = None

        if self._use_std_checker:
            if force_default_validator:
                self._validator_flags = validator_flags
            elif self._problem.checker is not None and self._problem.checker.name.startswith("std::"):
                self._validator_flags = self._config["flag"].get(self._problem.checker.name[5:], None)
            else:
                raise ProcessError("Logic error in auto_detect_std_checker.")

    def _write_ini(self) -> Polygon2DOMjudge:
        logger.info("[bold red blink]Add [italic]domjudge-problem.ini[/]:[/]", extra=dict(markup=True))
        ini_file = f"{self.temp_dir}/domjudge-problem.ini"
        ini_content = (
            f"short-name = {self.short_name}",
            f"timelimit = {self._problem.timelimit}",
            f"color = {self.color}",
            f"externalid = {self.external_id}",
        )
        for line in ini_content:
            logger.info(line)

        with open(ini_file, "w", encoding="utf-8") as f:
            f.write("\n".join(ini_content))
            f.write("\n")

        return self

    def _write_yaml(self) -> Polygon2DOMjudge:
        logger.info("[bold red blink]Add [italic]problem.yaml[/]:[/]", extra=dict(markup=True))
        yaml_content: Dict[str, Any] = dict(name=self._problem.name)
        memorylimit, outputlimit, passlimit = (
            self._problem.memorylimit,
            self._problem.outputlimit,
            self._problem.run_count,
        )
        if memorylimit > 0 or outputlimit > 0:
            yaml_content["limits"] = {}
            if memorylimit > 0:
                yaml_content["limits"]["memory"] = memorylimit
            if outputlimit > 0:
                yaml_content["limits"]["output"] = outputlimit

        yaml_file = self.temp_dir / "problem.yaml"
        output_validators_dir = self.temp_dir / "output_validators"
        checker_dir = output_validators_dir / "checker"
        interactor_dir = output_validators_dir / "interactor"

        if not self._problem.interactor is not None and self._use_std_checker:
            # can not support both interactor and checker
            checker_name = self._problem.checker.name if self._problem.checker is not None else UNKNOWN
            logger.info("Use std checker: %s", checker_name)
            yaml_content["validation"] = "default"
            if self._validator_flags:
                logger.info("Validator flags: %s", self._validator_flags)
                yaml_content["validator_flags"] = self._validator_flags
        elif passlimit == 1:
            ensure_dir(output_validators_dir)
            if self._problem.interactor is not None:
                logger.info("Use custom interactor.")
                yaml_content["validation"] = "custom interactive"
                interactor_file = self.package_dir / self._problem.interactor.path
                ensure_dir(interactor_dir)
                if interactor_file.suffix == ".cpp":
                    # only copy testlib.h when the interactor is written in C++
                    shutil.copyfile(TESTLIB_PATH, interactor_dir / "testlib.h")
                shutil.copyfile(interactor_file, interactor_dir / interactor_file.name)
            elif self._problem.checker is not None:
                logger.info("Use custom checker.")
                yaml_content["validation"] = "custom"
                checker_file = self.package_dir / self._problem.checker.path
                ensure_dir(checker_dir)
                if checker_file.suffix == ".cpp":
                    # only copy testlib.h when the checker is written in C++
                    shutil.copyfile(TESTLIB_PATH, checker_dir / "testlib.h")
                shutil.copyfile(checker_file, checker_dir / checker_file.name)
            else:
                logger.error("No checker found.")
                raise ProcessError("No checker found.")
        else:
            logger.info("Use multiple passes.")
            logger.warning("Multiple passes is an experimental feature.")
            logger.warning("It is not fully supported by DOMjudge.")
            logger.warning("Please ensure what you are doing.")
            assert passlimit == 2  # only support 2 passes in Polygon
            yaml_content["limits"]["validation_passes"] = passlimit
            yaml_content["validation"] = "custom multi-pass"
            ensure_dir(output_validators_dir)
            if self._problem.interactor is not None:
                logger.info("Use custom interactor.")
                interactor_file = self.package_dir / self._problem.interactor.path
                ensure_dir(interactor_dir)
                if interactor_file.suffix == ".cpp":
                    # only copy testlib.h when the interactor is written in C++
                    shutil.copyfile(TESTLIB_PATH, interactor_dir / "testlib.h")
                    Path(interactor_dir / "build").write_text(f"""#!/bin/sh
g++ -Wall -DDOMJUDGE -O2 {interactor_file.name} -std=gnu++20 -o run
""")
                    (interactor_dir / "build").chmod(0o755)
                shutil.copyfile(interactor_file, interactor_dir / interactor_file.name)
            else:
                logger.error("No interactor found.")
                raise ProcessError("No interactor found, not supported in multi-pass validation.")

        with open(yaml_file, "w", encoding="utf-8") as f:
            logger.info(yaml_content)
            yaml.dump(yaml_content, f, allow_unicode=True, default_flow_style=False)

        return self

    def _add_tests(self) -> Polygon2DOMjudge:
        logger.info("[bold red blink]Add tests:[/]", extra=dict(markup=True))

        ensure_dir(self.temp_dir / "data" / "sample")
        ensure_dir(self.temp_dir / "data" / "secret")
        sample_input_path_pattern = self._config["example_path_pattern"]["input"]
        sample_output_path_pattern = self._config["example_path_pattern"]["output"]

        def compare(src: StrPath, dst: StrPath):
            s, t = Path(src).name, Path(dst).name

            logger.debug("Compare %s and %s", s, t)
            with open(src, "r") as f1, open(dst, "r") as f2:
                return f1.read() != f2.read()

        for idx, test in enumerate(self._problem.tests, 1):
            input_src = self.package_dir / (self._problem.input_path_pattern % idx)
            output_src = self.package_dir / (self._problem.answer_path_pattern % idx)

            if test.sample and not self._hide_sample:
                # interactor can not support custom sample because DOMjudge always use sample input to test
                sample_input_src = self.package_dir / "statements" / self._problem.language / (sample_input_path_pattern % idx)
                sample_output_src = (
                    self.package_dir / "statements" / self._problem.language / (sample_output_path_pattern % idx)
                )
                # DOMjudge always use sample input to test, we can not use custom sample input
                # if the sample output is different from the output, use the sample output
                if sample_input_src.exists() and compare(input_src, sample_input_src):
                    logger.warning(
                        "Input file %s is different from the sample input file, please check it manually.",
                        input_src.name,
                    )
                if sample_output_src.exists() and compare(output_src, sample_output_src):
                    logger.warning(
                        "Output file %s is different from the sample output file, use the sample output.",
                        output_src.name,
                    )
                    if self._keep_sample and idx not in self._keep_sample:
                        output_src = sample_output_src
                input_dst = self.temp_dir / "data" / "sample" / f"{'%02d' % idx}.in"
                output_dst = self.temp_dir / "data" / "sample" / f"{'%02d' % idx}.ans"
                desc_dst = self.temp_dir / "data" / "sample" / f"{'%02d' % idx}.desc"

                logger.info("* sample: %02d.(in/ans) %s", idx, test.method)
            else:
                input_dst = self.temp_dir / "data" / "secret" / f"{'%02d' % idx}.in"
                output_dst = self.temp_dir / "data" / "secret" / f"{'%02d' % idx}.ans"
                desc_dst = self.temp_dir / "data" / "secret" / f"{'%02d' % idx}.desc"

                logger.debug("* secret: %02d.(in/ans) %s", idx, test.method)

            if self._problem.outputlimit > 0 and output_src.stat().st_size > self._problem.outputlimit * 1048576:
                logger.warning("Output file %s is exceed the output limit.", output_src.name)

            shutil.copyfile(input_src, input_dst)
            shutil.copyfile(output_src, output_dst)

            if test.__str__():
                logger.debug(test.__str__())
                with open(desc_dst, "w", encoding="utf-8") as f:
                    f.write(test.__str__())
                    f.write("\n")
        logger.info("Total %d tests.", len(self._problem.tests))
        return self

    def _add_jury_solutions(self) -> Polygon2DOMjudge:
        logger.info("[bold red blink]Add jury solutions:[/]", extra=dict(markup=True))

        for solution in self._problem.solutions:
            tag = solution.attrib["tag"]
            results = self._config["tag"].get(tag)

            if results is None:
                result_dir = self.temp_dir / "submissions" / "rejected"
            elif len(results) == 1:
                result_dir = self.temp_dir / "submissions" / results[0]
            else:
                result_dir = self.temp_dir / "submissions" / "mixed"

            if (source := solution.find("source[@path][@type]")) is not None:
                ensure_dir(self.temp_dir / "submissions" / result_dir)
                src = self.package_dir / source.attrib["path"]
                dst = self.temp_dir / "submissions" / result_dir / src.name
                lang = source.attrib["type"]
                self._add_solutions_with_expected_result(src, dst, lang, results)

        return self

    def _add_solutions_with_expected_result(self, src: Path, dst: Path, lang: str, results: Optional[List[Result]]) -> None:
        if results is None:
            logger.warning(
                "Find expected result with check_manually, you may add @EXPECTED_RESULTS@ in your source code for validation."
            )
            shutil.copyfile(src, dst)
            return

        def colorized(result: str) -> str:
            if result == "accepted":
                return f"[green italic]{result}[/]"
            if result == "wrong_answer":
                return f"[red italic]{result}[/]"
            return f"[yellow italic]{result}[/]"

        if len(results) == 1:
            logger.info("> %s: %s", src.name, colorized(results[0]), extra=dict(markup=True))
            shutil.copyfile(src, dst)
            return

        PROBLEM_RESULT_REMAP = {
            "ACCEPTED": "CORRECT",
            "WRONG_ANSWER": "WRONG-ANSWER",
            "TIME_LIMIT_EXCEEDED": "TIMELIMIT",
            "RUN_TIME_ERROR": "RUN-ERROR",
            "COMPILER_ERROR": "COMPILER-ERROR",
            "NO_OUTPUT": "NO-OUTPUT",
            "OUTPUT_LIMIT": "OUTPUT-LIMIT",
        }

        with open(src, "r") as f:
            content = f.read()

        if "@EXPECTED_RESULTS@" in content or "@EXPECTED_SCORE@" in content:
            logger.warning(
                "Find @EXPECTED_RESULTS@ or @EXPECTED_SCORE@ in %s, skip adding expected result.",
                src.name,
            )
            shutil.copyfile(src, dst)
        else:
            logger.info(
                "> %s: %s",
                src.name,
                ", ".join(map(colorized, results)),
                extra=dict(markup=True),
            )
            with open(dst, "w") as f:
                f.write(content)
                f.write("\n")
                lang = get_normalized_lang(lang)
                if comment_str := self._config["comment_str"].get(lang, None):
                    f.write(f"{comment_str} AUTO GENERATED BY POLYGON2DOMJUDGE\n")
                    f.write(
                        f"{comment_str} @EXPECTED_RESULTS@: {', '.join(map(lambda x: PROBLEM_RESULT_REMAP.get(x.upper(), x.upper()), results))}\n"
                    )
                else:
                    logger.warning(
                        "comment_str not found for type %s, skip adding expected result.",
                        lang,
                    )

    def _add_statement(self) -> Polygon2DOMjudge:
        if self._problem.statement is None:
            logger.warning("No statement found in problem.xml, skip adding statement.")
            return self

        ensure_dir(self.temp_dir / "problem_statement")
        logger.info("[bold red blink]Add statement:[/]", extra=dict(markup=True))
        logger.info("* %s", self._problem.statement)
        shutil.copyfile(
            self.package_dir / self._problem.statement,
            self.temp_dir / "problem_statement" / "problem.pdf",
        )
        return self

    def _add_attachments(self) -> Polygon2DOMjudge:
        if not self._problem.attachments:
            logger.warning("No attachments found in problem.xml, skip adding attachments.")
            return self

        ensure_dir(self.temp_dir / "attachments")
        logger.info("[bold red blink]Add attachments:[/]", extra=dict(markup=True))
        for attachment in self._problem.attachments:
            logger.info("* %s", attachment.name)
            shutil.copyfile(
                self.package_dir / attachment,
                self.temp_dir / "attachment" / attachment.name,
            )
        return self

    def _archive(self):
        shutil.make_archive(self.output_file.as_posix(), "zip", self.temp_dir)
        logger.info("Make package %s.zip success.", self.output_file.name)
        return self

    def override_memory_limit(self, memory_limit: int) -> Polygon2DOMjudge:
        if not isinstance(memory_limit, int):
            raise TypeError("memory_limit must be an integer.")
        if self._problem.memorylimit == memory_limit:
            return self
        logger.info("Override memory limit: %dMB", memory_limit)
        self._problem.memorylimit = memory_limit
        return self

    def override_output_limit(self, output_limit: int) -> Polygon2DOMjudge:
        if not isinstance(output_limit, int):
            raise TypeError("output_limit must be an integer.")
        if self._problem.outputlimit == output_limit:
            return self
        logger.info("Override output limit: %dMB", output_limit)
        self._problem.outputlimit = output_limit
        return self

    def process(self) -> None:
        self._write_ini()._write_yaml()._add_tests()._add_jury_solutions()
        if self._with_statement:
            self._add_statement()
        if self._with_attachments:
            self._add_attachments()
        self._archive()


class Options(TypedDict, total=False):
    force_default_validator: bool
    auto_detect_std_checker: bool
    validator_flags: Optional[str]
    hide_sample: bool
    keep_sample: Optional[Sequence[int]]
    config: Optional[Config]
    memory_limit: Optional[int]
    output_limit: Optional[int]
    testset_name: Optional[str]
    external_id: Optional[str]
    with_statement: bool
    with_attachments: bool
    test_set: Optional[str]


def convert(
    package: StrPath,
    output: Optional[StrPath] = None,
    *,
    short_name: Optional[str] = None,
    color: str = DEFAULT_COLOR,
    confirm: Callable[[], bool] = lambda: True,
    **kwargs: Unpack[Options],
) -> None:
    """Convert a Polygon package to a DOMjudge package.

    Args:
        package (StrPath): The path to the polygon package directory.
        output (Optional[StrPath], optional): The path to the output DOMjudge package.
        short_name (Optional[Str], optional): The short name of the problem.
        color (str, optional): The color of the problem.

    Raises:
        ProcessError: If convert failed.
        FileNotFoundError: If the package is not found.
        FileExistsError: If the output file already exists.
    """

    config = cast(Config, load_config(DEFAULT_CONFIG_FILE))

    if short_name is None:
        raise ValueError("short_name is required.")

    # config override
    if kwargs.get("config") is not None:
        update_dict(config, cast(Config, kwargs["config"]))

    with (
        tempfile.TemporaryDirectory(prefix="p2d-polygon-") as polygon_temp_dir,
        tempfile.TemporaryDirectory(prefix="p2d-domjudge-") as domjudge_temp_dir,
    ):
        package_dir = Path(package).resolve()
        if package_dir.is_file():
            with zipfile.ZipFile(package, "r") as zip_ref:
                logger.info("Extracting %s to %s", package_dir.name, polygon_temp_dir)
                package_dir = Path(polygon_temp_dir)
                zip_ref.extractall(package_dir)
        elif package_dir.is_dir():
            logger.info("Using %s", package_dir)
        else:
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), package_dir.name)

        if output:
            if Path(output).name.endswith(".zip"):
                output_file = Path(output).with_suffix("").resolve()
            else:
                output_file = Path(output).resolve() / short_name
        else:
            output_file = Path.cwd() / short_name

        if output_file.with_suffix(".zip").resolve().exists():
            raise FileExistsError(
                errno.EEXIST,
                os.strerror(errno.EEXIST),
                f"{output_file.with_suffix('.zip')}",
            )

        logger.info("This is Polygon2DOMjudge by cubercsl.")
        logger.info("Process Polygon Package to DOMjudge Package.")
        logger.info("Version: %s", __version__)

        if sys.platform.startswith("win"):
            logger.warning("It is not recommended running on windows.")  # pragma: no cover

        logger.info("Package directory: %s", package_dir)
        logger.info("Output file: %s.zip", output_file)

        _kwargs: _Polygon2DOMjudgeArgs = {
            "hide_sample": kwargs.get("hide_sample", False),
            "auto_detect_std_checker": kwargs.get("auto_detect_std_checker", False),
            "force_default_validator": kwargs.get("force_default_validator", False),
            "validator_flags": kwargs.get("validator_flags", None),
            "testset_name": kwargs.get("testset_name", None),
            "external_id": kwargs.get("external_id", None),
            "with_statement": kwargs.get("with_statement", False),
            "with_attachments": kwargs.get("with_attachments", False),
            "config": config,
        }

        p = Polygon2DOMjudge(package_dir, domjudge_temp_dir, output_file, short_name, color, **_kwargs)

        if kwargs.get("memory_limit"):
            p.override_memory_limit(cast(int, kwargs["memory_limit"]))
        if kwargs.get("output_limit"):
            p.override_output_limit(cast(int, kwargs["output_limit"]))

        if confirm():
            p.process()
