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
from typing import cast, Any, Dict, List, Optional, Sequence, Tuple, TypedDict, TYPE_CHECKING
from xml.etree.ElementTree import Element

import yaml

from . import __version__
from .typing import Config, ValidatorFlags, Result
from .utils import ensure_dir, load_config, update_dict, get_normalized_lang

if sys.version_info < (3, 11):
    from typing_extensions import Unpack
else:
    from typing import Unpack

if TYPE_CHECKING:
    from _typeshed import StrPath

logger = logging.getLogger(__name__)

DEFAULT_ASSET_PATH = Path(__file__).resolve().parent / 'asset'
DEFAULT_TESTLIB_PATH = Path(__file__).resolve().parent / 'testlib'
DEFAULT_CONFIG_FILE = Path(os.getenv('CONFIG_PATH', DEFAULT_ASSET_PATH)) / 'config.toml'
DEFAULT_COLOR = '#000000'
UNKNOWN = 'unknown'

TESTLIB_PATH = (Path(os.getenv('TESTLIB_PATH', DEFAULT_TESTLIB_PATH)) / 'testlib.h').resolve()


class _Polygon2DOMjudgeArgs(TypedDict, total=False):
    force_default_validator: bool
    auto_detect_std_checker: bool
    validator_flags: ValidatorFlags
    hide_sample: bool
    testset_name: Optional[str]
    external_id: Optional[str]
    without_statement: bool
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
            'english',
            'russian',
            'chinese',
        )

        _SHORT_NAME_FILTER = re.compile(r'[^a-zA-Z0-9-_]')

        class Test:
            def __init__(
                self,
                method: str,
                description: Optional[str] = None,
                cmd: Optional[str] = None,
                sample: bool = False
            ) -> None:
                self.method = method
                self.description = description
                self.cmd = cmd
                self.sample = sample

            def __str__(self) -> str:
                description = self.description if self.description else ''
                cmd = f'[GEN] {self.cmd}' if self.cmd else ''
                return f'{description} {cmd}'.strip()

        class Executable:
            def __init__(self, path: str, name: str = UNKNOWN, **kwargs) -> None:
                self.path = path
                self.name = name

            @staticmethod
            def from_element(ele: Optional[Element]) -> Optional[Polygon2DOMjudge.Problem.Executable]:
                if ele is not None and (source := ele.find('source')) is not None:
                    return Polygon2DOMjudge.Problem.Executable(
                        source.attrib['path'],
                        ele.attrib.get('name', UNKNOWN)
                    )
                return None

        def __init__(
            self,
            problem_xml: StrPath, /,
            **kwargs: Unpack[_ProblemArgs]
        ) -> None:
            """Initialize the problem class from problem.xml.

            Args:
                problem_xml (StrPath): Path to problem.xml.

            Raises:
                ProcessError: If some mandatory fields are missing or invalid.
            """

            language_preference = kwargs.get('language_preference', self._LANGUAGE_PREFERENCE)
            testset_name = kwargs.get('testset_name', None)

            problem = xml.etree.ElementTree.parse(problem_xml).getroot()
            short_name = self._SHORT_NAME_FILTER.sub('', problem.attrib.get('short-name', ''))
            name, language = self._get_preference_name(problem.find('names'), language_preference)
            statement = self._get_statement(problem.find('statements'), language)

            testset = self._get_testset(problem, testset_name)

            timelimit = testset.find('time-limit')
            memorylimit = testset.find('memory-limit')
            input_path_pattern = testset.find('input-path-pattern')
            answer_path_pattern = testset.find('answer-path-pattern')

            if not short_name:
                logger.error('Short name is invalid in problem.xml.')
                raise ProcessError('Short name is invalid in problem.xml.')

            if timelimit is None or timelimit.text is None or not timelimit.text.isdigit():
                logger.error('Time limit is invalid in problem.xml.')
                raise ProcessError('Time limit is invalid in problem.xml.')

            if memorylimit is None or memorylimit.text is None or not memorylimit.text.isdigit():
                logger.error('Memory limit is invalid in problem.xml.')
                raise ProcessError('Memory limit is invalid in problem.xml.')

            if input_path_pattern is None or input_path_pattern.text is None:
                logger.error('Input path pattern is invalid in problem.xml.')
                raise ProcessError('Input path pattern is invalid in problem.xml.')

            if answer_path_pattern is None or answer_path_pattern.text is None:
                logger.error('Answer path pattern is invalid in problem.xml.')
                raise ProcessError('Answer path pattern is invalid in problem.xml.')

            self.short_name = short_name
            self.name = name
            self.language = language
            self.timelimit = int(timelimit.text) / 1000.0
            self.memorylimit = int(memorylimit.text) // 1048576
            self.outputlimit = -1
            self.input_path_pattern = input_path_pattern.text
            self.answer_path_pattern = answer_path_pattern.text
            self.checker = self.Executable.from_element(problem.find('assets/checker[source]'))
            self.interactor = self.Executable.from_element(problem.find('assets/interactor[source]'))
            self.tests = tuple(
                self.Test(
                    method=test.attrib['method'],
                    description=test.attrib.get('description', None),
                    cmd=test.attrib.get('cmd', None),
                    sample=bool(test.attrib.get('sample', False))
                ) for test in testset.findall('tests/test')
            )
            self.solutions = tuple(problem.findall('assets/solutions/solution[@tag]'))
            self.statement = statement

        @staticmethod
        def _get_preference_name(
            names: Optional[Element],
            language_preference: Sequence[str] = _LANGUAGE_PREFERENCE
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
                logger.error('Can not find names in problem.xml.')
                raise ProcessError('Can not find names in problem.xml.')

            for lang in language_preference:
                name = names.find(f'name[@language="{lang}"]')
                if name is not None and 'value' in name.attrib and 'language' in name.attrib:
                    return name.attrib['value'], name.attrib['language']

            # if no preference language found, return the first name
            name = names.find('name')
            if name is not None and 'value' in name.attrib and 'language' in name.attrib:
                return name.attrib['value'], name.attrib['language']

            logger.error('Name is invalid in problem.xml.')
            raise ProcessError('Name is invalid in problem.xml.')

        @staticmethod
        def _get_testset(problem: Element, testset_name: Optional[str]) -> Element:
            # if testset_name is not specified, use the only testset if there is only one testset
            if testset_name is None:
                if t := problem.findall('judging/testset'):
                    if len(t) == 1:
                        return t[0]
                    logger.error('Multiple testsets found in problem.xml.')
                    logger.error('Please specify the testset name in the command line.')
                    raise ProcessError('Multiple testsets found in problem.xml.')
                logger.error(f'Can not find any testset in problem.xml.')
                raise ProcessError(f'Can not find any testset in problem.xml.')

            # find testset by name
            if (ele := problem.find(f'judging/testset[@name="{testset_name}"]')) is None:
                logger.error(f'Can not find testset {testset_name} in problem.xml.')
                raise ProcessError(f'Can not find testset {testset_name} in problem.xml.')
            return ele

        @staticmethod
        def _get_statement(statements: Optional[Element], language: str) -> Optional[StrPath]:
            if statements is None:
                return None

            if (statement := statements.find(f'statement[@language="{language}"][@type="application/pdf"][@path]')) is None:
                logger.warning(f'Can not find statement in {language} in problem.xml, this will skip adding statement.')
                return None

            return statement.attrib['path']

    """Polygon to DOMjudge package.
    """

    def __init__(
        self,
        package_dir: StrPath,
        temp_dir: StrPath,
        output_file: StrPath,
        short_name: str, /,
        color: str = DEFAULT_COLOR,
        **kwargs: Unpack[_Polygon2DOMjudgeArgs]
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

        force_default_validator = kwargs.get('force_default_validator', False)
        auto_detect_std_checker = kwargs.get('auto_detect_std_checker', False)
        validator_flags = kwargs.get('validator_flags', cast(ValidatorFlags, ()))
        hide_sample = kwargs.get('hide_sample', False)
        testset_name = kwargs.get('testset_name', None)
        external_id = kwargs.get('external_id', None)
        without_statement = kwargs.get('without_statement', False)
        config = kwargs.get('config', cast(Config, load_config(DEFAULT_CONFIG_FILE)))

        self.package_dir = Path(package_dir)
        self.short_name = short_name
        self.color = color
        self.temp_dir = Path(temp_dir)
        self.output_file = Path(output_file)
        self.without_statement = without_statement

        self._config = config

        logger.debug('Parse \'problem.xml\':')
        if testset_name:
            logger.debug(f'With testset_name: {testset_name}')
        self._problem = self.Problem(
            self.package_dir / 'problem.xml',
            language_preference=self._config['language_preference'],
            testset_name=testset_name,
        )
        self.external_id = external_id if external_id else self._problem.short_name

        if force_default_validator and auto_detect_std_checker:
            logger.error('Can not use auto_detect_std_checker and force_default_validator at the same time.')
            raise ValueError('Can not use auto_detect_std_checker and force_default_validator at the same time.')

        self._replace_sample = not hide_sample  # always replace sample with the sample in statements when hide_sample is False
        self._hide_sample = hide_sample or self._problem.interactor is not None
        self._use_std_checker = auto_detect_std_checker and \
            self._problem.checker is not None and self._problem.checker.name.startswith('std::') or \
            force_default_validator
        self._validator_flags: ValidatorFlags = ()

        if self._use_std_checker:
            if force_default_validator:
                self._validator_flags = validator_flags
            elif self._problem.checker is not None and self._problem.checker.name.startswith('std::'):
                self._validator_flags = cast(ValidatorFlags,
                                             self._config['flag'].get(self._problem.checker.name[5:], ()))
            else:
                raise ProcessError('Logic error in auto_detect_std_checker.')

    def _write_ini(self) -> Polygon2DOMjudge:
        logger.debug('Add \'domjudge-problem.ini\':')
        ini_file = f'{self.temp_dir}/domjudge-problem.ini'
        ini_content = (f'short-name = {self.short_name}',
                       f'timelimit = {self._problem.timelimit}',
                       f'color = {self.color}',
                       f'externalid = {self.external_id}')
        for line in ini_content:
            logger.info(line)

        with open(ini_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(ini_content))
            f.write('\n')

        return self

    def _write_yaml(self) -> Polygon2DOMjudge:
        logger.debug('Add \'problem.yaml\':')
        yaml_content: Dict[str, Any] = dict(name=self._problem.name)
        memorylimit, outputlimit = self._problem.memorylimit, self._problem.outputlimit
        if memorylimit > 0 or outputlimit > 0:
            yaml_content['limits'] = {}
            if memorylimit > 0:
                yaml_content['limits']['memory'] = memorylimit
            if outputlimit > 0:
                yaml_content['limits']['output'] = outputlimit

        yaml_file = self.temp_dir / 'problem.yaml'
        output_validators_dir = self.temp_dir / 'output_validators'
        checker_dir = output_validators_dir / 'checker'
        interactor_dir = output_validators_dir / 'interactor'

        if not self._problem.interactor is not None and self._use_std_checker:
            # can not support both interactor and checker
            checker_name = self._problem.checker.name if self._problem.checker is not None else UNKNOWN
            logger.info(f'Use std checker: {checker_name}')
            yaml_content['validation'] = 'default'
            if self._validator_flags:
                logger.info(f'Validator flags: {" ".join(self._validator_flags)}')
                yaml_content['validator_flags'] = ' '.join(self._validator_flags)
        else:
            ensure_dir(output_validators_dir)
            if self._problem.interactor is not None:
                logger.info('Use custom interactor.')
                yaml_content['validation'] = 'custom interactive'
                interactor_file = self.package_dir / self._problem.interactor.path
                ensure_dir(interactor_dir)
                if interactor_file.suffix == '.cpp':
                    # only copy testlib.h when the interactor is written in C++
                    shutil.copyfile(TESTLIB_PATH, interactor_dir / 'testlib.h')
                shutil.copyfile(interactor_file, interactor_dir / interactor_file.name)
            elif self._problem.checker is not None:
                logger.info('Use custom checker.')
                yaml_content['validation'] = 'custom'
                checker_file = self.package_dir / self._problem.checker.path
                ensure_dir(checker_dir)
                if checker_file.suffix == '.cpp':
                    # only copy testlib.h when the checker is written in C++
                    shutil.copyfile(TESTLIB_PATH, checker_dir / 'testlib.h')
                shutil.copyfile(checker_file, checker_dir / checker_file.name)
            else:
                logger.error('No checker found.')
                raise ProcessError('No checker found.')

        with open(yaml_file, 'w', encoding='utf-8') as f:
            yaml.dump(yaml_content, f, allow_unicode=True, default_flow_style=False)

        return self

    def _add_tests(self) -> Polygon2DOMjudge:
        logger.debug('Add tests:')

        ensure_dir(self.temp_dir / 'data' / 'sample')
        ensure_dir(self.temp_dir / 'data' / 'secret')
        sample_input_path_pattern = self._config['example_path_pattern']['input']
        sample_output_path_pattern = self._config['example_path_pattern']['output']

        def compare(src: StrPath, dst: StrPath):
            s, t = Path(src).name, Path(dst).name

            logger.debug(f'Compare {s} and {t}')
            with open(src, 'r') as f1, open(dst, 'r') as f2:
                if f1.read() != f2.read():
                    logger.warning(f'{s} and {t} are not the same, use {t}.')

        for idx, test in enumerate(self._problem.tests, 1):
            input_src = self.package_dir / (self._problem.input_path_pattern % idx)
            output_src = self.package_dir / (self._problem.answer_path_pattern % idx)

            if test.sample and not self._hide_sample:
                # interactor can not support custom sample because DOMjudge always use sample input to test
                sample_input_src = (
                    self.package_dir / 'statements' / self._problem.language / (sample_input_path_pattern % idx))
                sample_output_src = (
                    self.package_dir / 'statements' / self._problem.language / (sample_output_path_pattern % idx))
                if self._replace_sample and sample_input_src.exists():
                    compare(input_src, sample_input_src)
                    input_src = sample_input_src
                if self._replace_sample and sample_output_src.exists():
                    compare(output_src, sample_output_src)
                    output_src = sample_output_src
                input_dst = self.temp_dir / 'data' / 'sample' / f'{"%02d" % idx}.in'
                output_dst = self.temp_dir / 'data' / 'sample' / f'{"%02d" % idx}.ans'
                desc_dst = self.temp_dir / 'data' / 'sample' / f'{"%02d" % idx}.desc'

                logger.info(f'* sample: {"%02d" % idx}.(in/ans) {test.method}')
            else:
                input_dst = self.temp_dir / 'data' / 'secret' / f'{"%02d" % idx}.in'
                output_dst = self.temp_dir / 'data' / 'secret' / f'{"%02d" % idx}.ans'
                desc_dst = self.temp_dir / 'data' / 'secret' / f'{"%02d" % idx}.desc'

                logger.info(f'* secret: {"%02d" % idx}.(in/ans) {test.method}')

            if self._problem.outputlimit > 0 and output_src.stat().st_size > self._problem.outputlimit * 1048576:
                logger.warning(f'Output file {output_src.name} is exceed the output limit.')

            shutil.copyfile(input_src, input_dst)
            shutil.copyfile(output_src, output_dst)

            if test.__str__():
                logger.info(f'{test.__str__()}')
                with open(desc_dst, 'w', encoding='utf-8') as f:
                    f.write(test.__str__())
                    f.write('\n')

        return self

    def _add_jury_solutions(self) -> Polygon2DOMjudge:
        logger.debug('Add jury solutions:')

        for solution in self._problem.solutions:
            tag = solution.attrib['tag']
            logger.info(f'Add jury solution: {tag}')
            results = self._config['tag'].get(tag)

            if results is None:
                result_dir = self.temp_dir / 'submissions' / 'rejected'
            elif len(results) == 1:
                result_dir = self.temp_dir / 'submissions' / results[0]
            else:
                result_dir = self.temp_dir / 'submissions' / 'mixed'

            if (source := solution.find('source[@path][@type]')) is not None:
                ensure_dir(self.temp_dir / 'submissions' / result_dir)
                src = self.package_dir / source.attrib['path']
                dst = self.temp_dir / 'submissions' / result_dir / src.name
                lang = source.attrib['type']
                self._add_solutions_with_expected_result(src, dst, lang, results)

        return self

    def _add_solutions_with_expected_result(self, src: Path, dst: Path, lang: str,  results: Optional[List[Result]]) -> None:
        if results is None:
            logger.warning(
                f'Find expected result with check_manually, you may add @EXPECTED_RESULTS@ in your source code for validation.')
            shutil.copyfile(src, dst)
            return

        if len(results) == 1:
            logger.info(f'- {src.name}: Expected result: {results[0]}')
            shutil.copyfile(src, dst)
            return

        PROBLEM_RESULT_REMAP = {
            'ACCEPTED': 'CORRECT',
            'WRONG_ANSWER': 'WRONG-ANSWER',
            'TIME_LIMIT_EXCEEDED': 'TIMELIMIT',
            'RUN_TIME_ERROR': 'RUN-ERROR',
            'COMPILER_ERROR': 'COMPILER-ERROR',
            'NO_OUTPUT': 'NO-OUTPUT',
            'OUTPUT_LIMIT': 'OUTPUT-LIMIT'
        }

        with open(src, 'r') as f:
            content = f.read()

        if '@EXPECTED_RESULTS@' in content or '@EXPECTED_SCORE@' in content:
            logger.warning(
                f'Find @EXPECTED_RESULTS@ or @EXPECTED_SCORE@ in {src.name}, skip adding expected result.')
            shutil.copyfile(src, dst)
        else:
            logger.info(
                f'- {src.name}: Expected result: {", ".join(map(lambda x: PROBLEM_RESULT_REMAP[x.upper()].lower(), results))}')
            with open(dst, 'w') as f:
                f.write(content)
                f.write('\n')
                lang = get_normalized_lang(lang)
                if comment_str := self._config['comment_str'].get(lang, None):
                    f.write(f'{comment_str} AUTO GENERATED BY POLYGON2DOMJUDGE\n')
                    f.write(
                        f'{comment_str} @EXPECTED_RESULTS@: {", ".join(map(lambda x: PROBLEM_RESULT_REMAP.get(x.upper(), x.upper()), results))}\n')
                else:
                    logger.warning(f'comment_str not found for type {lang}, skip adding expected result.')

    def _add_statement(self) -> Polygon2DOMjudge:
        if self._problem.statement is None:
            logger.warning('No statement found in problem.xml, skip adding statement.')
            return self

        if self.without_statement:
            logger.info('Skip adding statement due to --without-statement flag.')
            return self

        ensure_dir(self.temp_dir / 'problem_statement')
        logger.debug('Add statement:')
        logger.info(f'* {self._problem.statement}')
        shutil.copyfile(self.package_dir / self._problem.statement, self.temp_dir / 'problem_statement' / 'problem.pdf')
        return self

    def _archive(self):
        shutil.make_archive(self.output_file.as_posix(), 'zip', self.temp_dir, logger=logger)
        logger.info(f'Make package {self.output_file.name}.zip success.')
        return self

    def override_memory_limit(self, memory_limit: int) -> Polygon2DOMjudge:
        if not isinstance(memory_limit, int):
            raise TypeError('memory_limit must be an integer.')
        if self._problem.memorylimit == memory_limit:
            return self
        logger.info(f'Override memory limit: {memory_limit}')
        self._problem.memorylimit = memory_limit
        return self

    def override_output_limit(self, output_limit: int) -> Polygon2DOMjudge:
        if not isinstance(output_limit, int):
            raise TypeError('output_limit must be an integer.')
        if self._problem.outputlimit == output_limit:
            return self
        logger.info(f'Override output limit: {output_limit}')
        self._problem.outputlimit = output_limit
        return self

    def process(self) -> Polygon2DOMjudge:
        return self._write_ini() \
            ._write_yaml() \
            ._add_tests() \
            ._add_jury_solutions() \
            ._add_statement() \
            ._archive()


def _confirm(
    package_dir: StrPath,
    output_file: StrPath,
    argv: List[str] = sys.argv,
    skip_confirmation: bool = False
) -> None:
    logger.info('This is Polygon2DOMjudge by cubercsl.')
    logger.info('Process Polygon Package to DOMjudge Package.')
    logger.info("Version: {}".format(__version__))

    if sys.platform.startswith('win'):
        logger.warning('It is not recommended running on windows.')

    logger.info(f'Arguments: {" ".join(argv[1:])}')
    logger.info(f'Package directory: {package_dir}')
    logger.info(f'Output file: {output_file}.zip')
    if not skip_confirmation:
        if input('Are you sure to continue? [y/N]').lower() == 'y':
            return
        sys.exit(0)


class Options(TypedDict, total=False):
    force_default_validator: bool
    auto_detect_std_checker: bool
    validator_flags: ValidatorFlags
    hide_sample: bool
    config: Optional[Config]
    memory_limit: int
    output_limit: int
    skip_confirmation: bool
    testset_name: Optional[str]
    external_id: Optional[str]
    without_statement: bool
    code: str  # alias of short_name


def convert(
    package: StrPath,
    output: Optional[StrPath] = None, *,
    short_name: Optional[str] = None,
    color: str = DEFAULT_COLOR,
    **kwargs: Unpack[Options]
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

    if kwargs.get('code'):  # code is alias of short_name
        short_name = cast(str, kwargs['code'])

    _kwargs: _Polygon2DOMjudgeArgs = {
        'hide_sample': kwargs.get('hide_sample', False),
        'auto_detect_std_checker': kwargs.get('auto_detect_std_checker', False),
        'force_default_validator': kwargs.get('force_default_validator', False),
        'validator_flags': kwargs.get('validator_flags', []),
        'testset_name': kwargs.get('testset_name', None),
        'external_id': kwargs.get('external_id', None),
        'without_statement': kwargs.get('without_statement', False),
        'config': load_config(DEFAULT_CONFIG_FILE),
    }

    if short_name is None:
        raise ValueError('short_name is required.')

    # config override
    if kwargs.get('config') is not None:
        update_dict(_kwargs['config'], cast(Config, kwargs['config']))

    skip_confirmation = kwargs.get('skip_confirmation', False)

    with tempfile.TemporaryDirectory(prefix='p2d-polygon-') as polygon_temp_dir, \
            tempfile.TemporaryDirectory(prefix='p2d-domjudge-') as domjudge_temp_dir:
        package_dir = Path(package).resolve()
        if package_dir.is_file():
            with zipfile.ZipFile(package, 'r') as zip_ref:
                logger.info(f'Extracting {package_dir.name} to {polygon_temp_dir}')
                package_dir = Path(polygon_temp_dir)
                zip_ref.extractall(package_dir)
        elif package_dir.is_dir():
            logger.info(f'Using {package_dir}')
        else:
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), package_dir.name)

        if output:
            if Path(output).name.endswith('.zip'):
                output_file = Path(output).with_suffix('').resolve()
            else:
                output_file = Path(output).resolve() / short_name
        else:
            output_file = Path.cwd() / short_name

        if output_file.with_suffix('.zip').resolve().exists():
            raise FileExistsError(errno.EEXIST, os.strerror(errno.EEXIST), f'{output_file.with_suffix(".zip")}')

        _confirm(package_dir, output_file, sys.argv, skip_confirmation=skip_confirmation)

        p = Polygon2DOMjudge(package_dir, domjudge_temp_dir, output_file, short_name, color, **_kwargs)

        if kwargs.get('memory_limit'):
            p.override_memory_limit(cast(int, kwargs['memory_limit']))
        if kwargs.get('output_limit'):
            p.override_output_limit(cast(int, kwargs['output_limit']))
        p.process()


__all__ = [
    'convert',
    'DEFAULT_COLOR',
    'DEFAULT_CONFIG_FILE',
    'Options',
    'Polygon2DOMjudge',
    'ProcessError',
]
