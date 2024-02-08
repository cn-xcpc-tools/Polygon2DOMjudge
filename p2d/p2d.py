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
from typing import cast, Any, Dict, Optional, Sequence, Tuple, Type, TypedDict, TYPE_CHECKING
from xml.etree.ElementTree import Element

import yaml

from . import __version__
from .typing import Config, ValidatorFlags, Tag, Result
from .utils import ensure_dir, load_config

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
DEFAULT_CODE = 'PROB1'
DEFAULT_COLOR = '#000000'
UNKNOWN = 'unknown'

TESTLIB_PATH = (Path(os.getenv('TESTLIB_PATH', DEFAULT_TESTLIB_PATH)) / 'testlib.h').resolve()
EXTENSION_FOR_DESC = os.getenv('EXTENSION_FOR_DESC', '.desc')


class _Polygon2DOMjudgeArgs(TypedDict, total=False):
    force_default_validator: bool
    auto_detect_std_checker: bool
    validator_flags: ValidatorFlags
    replace_sample: bool
    hide_sample: bool
    config: Config
    problem_cls: Type[Problem]
    test_cls: Type[Test]


class _ProblemArgs(TypedDict, total=False):
    language_preference: Sequence[str]
    test_cls: Type[Test]


class ProcessError(RuntimeError):
    pass


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

    def __str__(self):
        return f'{self.description} {"[GEN] " + self.cmd if self.cmd else ""}'.strip()


class Problem:
    """
    The problem class.
    """

    _LANGUAGE_PREFERENCE = (
        'english',
        'russian',
        'chinese',
    )

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
        _Test = kwargs.get('test_cls', Test)

        root = xml.etree.ElementTree.parse(problem_xml)
        name, language = self._get_preference_name(root.find('names'), language_preference)

        testset = root.find('judging/testset')
        if testset is None:
            logger.error('Can not find testset in problem.xml.')
            raise ProcessError('Can not find testset in problem.xml.')

        timelimit = testset.find('time-limit')
        memorylimit = testset.find('memory-limit')
        input_path_pattern = testset.find('input-path-pattern')
        answer_path_pattern = testset.find('answer-path-pattern')

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

        self.name = name
        self.language = language
        self.timelimit = int(timelimit.text) / 1000.0
        self.memorylimit = int(memorylimit.text) // 1048576
        self.outputlimit = -1
        self.input_path_pattern = input_path_pattern.text
        self.answer_path_pattern = answer_path_pattern.text
        self.checker = root.find('assets/checker')
        self.interactor = root.find('assets/interactor')
        self.tests = tuple(
            _Test(
                method=test.attrib['method'],
                description=test.attrib.get('description', None),
                cmd=test.attrib.get('cmd', None),
                sample=bool(test.attrib.get('sample', False))
            ) for test in testset.findall('tests/test')
        )

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

    @property
    def has_interactor(self):
        return self.interactor is not None

    @property
    def has_checker(self):
        return self.checker is not None

    @property
    def has_std_checker(self):
        return self.checker_name.startswith('std::')

    @property
    def checker_name(self):
        if self.checker is None:
            return UNKNOWN
        return self.checker.attrib.get('name', UNKNOWN)

    @property
    def interactor_name(self):
        if self.interactor is None:
            return UNKNOWN
        return self.interactor.attrib.get('name', UNKNOWN)

    @property
    def checker_path(self):
        return self.checker.find('source').attrib['path']

    @property
    def interactor_path(self):
        return self.interactor.find('source').attrib['path']


class Polygon2DOMjudge:
    """Polygon to DOMjudge package.
    """

    def __init__(
        self,
        package_dir: StrPath,
        temp_dir: StrPath,
        output_file: StrPath, /,
        short_name: str = DEFAULT_CODE,
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
        replace_sample = kwargs.get('replace_sample', False)
        hide_sample = kwargs.get('hide_sample', False)
        config = kwargs.get('config', cast(Config, load_config(DEFAULT_CONFIG_FILE)))

        _Problem = kwargs.get('problem_cls', Problem)
        _Test = kwargs.get('test_cls', Test)

        self.package_dir = Path(package_dir)
        self.short_name = short_name
        self.color = color
        self.temp_dir = Path(temp_dir)
        self.output_file = Path(output_file)

        self._config = config

        logger.debug('Parse \'problem.xml\':')
        self._problem = _Problem(
            self.package_dir / 'problem.xml',
            language_preference=self._config['language_preference'],
            test_cls=_Test
        )

        if force_default_validator and auto_detect_std_checker:
            logger.error('Can not use auto_detect_std_checker and force_default_validator at the same time.')
            raise ValueError('Can not use auto_detect_std_checker and force_default_validator at the same time.')

        self._replace_sample = replace_sample
        self._hide_sample = hide_sample or self._problem.has_interactor
        self._use_std_checker = auto_detect_std_checker and self._problem.has_std_checker or force_default_validator
        self._validator_flags: ValidatorFlags = ()

        if self._use_std_checker:
            if force_default_validator:
                self._validator_flags = validator_flags
            else:
                self._validator_flags = cast(ValidatorFlags,
                                             self._config['flag'].get(self._problem.checker_name[5:], ()))

    def _write_ini(self) -> Polygon2DOMjudge:
        logger.debug('Add \'domjudge-problem.ini\':')
        ini_file = f'{self.temp_dir}/domjudge-problem.ini'
        ini_content = (f'short-name = {self.short_name}',
                       f'timelimit = {self._problem.timelimit}',
                       f'color = {self.color}')
        for line in ini_content:
            logger.info(line)

        with open(ini_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(ini_content) + '\n')

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
        checker_name = self._problem.checker_name

        if not self._problem.has_interactor and self._use_std_checker:
            # can not support both interactor and checker
            logger.info(f'Use std checker: {checker_name}')
            yaml_content['validation'] = 'default'
            if self._validator_flags:
                logger.info(f'Validator flags: {" ".join(self._validator_flags)}')
                yaml_content['validator_flags'] = ' '.join(self._validator_flags)
        else:
            ensure_dir(output_validators_dir)
            if self._problem.has_interactor:
                logger.info('Use custom interactor.')
                yaml_content['validation'] = 'custom interactive'
                interactor_file = self.package_dir / self._problem.interactor_path
                ensure_dir(interactor_dir)
                shutil.copyfile(TESTLIB_PATH, interactor_dir / 'testlib.h')
                shutil.copyfile(interactor_file, interactor_dir / 'interactor.cpp')
            elif self._problem.has_checker:
                logger.info('Use custom checker.')
                yaml_content['validation'] = 'custom'
                checker_file = self.package_dir / self._problem.checker_path
                ensure_dir(checker_dir)
                shutil.copyfile(TESTLIB_PATH, checker_dir / 'testlib.h')
                shutil.copyfile(checker_file, checker_dir / 'checker.cpp')
            else:
                logger.error('No checker found.')
                raise ProcessError('No checker found.')

        with open(yaml_file, 'w') as f:
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

        return self

    def _add_jury_solutions(self) -> Polygon2DOMjudge:
        logger.debug('Add jury solutions:')

        ensure_dir(self.temp_dir / 'submissions' / 'accepted')
        ensure_dir(self.temp_dir / 'submissions' / 'wrong_answer')
        ensure_dir(self.temp_dir / 'submissions' / 'time_limit_exceeded')
        ensure_dir(self.temp_dir / 'submissions' / 'run_time_error')

        for desc in filter(lambda x: x.name.endswith(EXTENSION_FOR_DESC), (self.package_dir / 'solutions').iterdir()):
            solution, result = self._get_submission_and_result(desc)
            src = self.package_dir / 'solutions' / solution
            dst = self.temp_dir / 'submissions' / result / solution
            logger.info(f'- {solution} (Expected Result: {result})')
            shutil.copyfile(src, dst)

        return self

    def _archive(self):
        shutil.make_archive(self.output_file.name, 'zip', self.temp_dir, logger=logger)
        logger.info(f'Make package {self.output_file.name}.zip success.')
        return self

    def _get_submission_and_result(self, desc: StrPath) -> Tuple[str, Result]:

        file_name_pat = re.compile(r'File name: (?P<value>.*)')
        tag_pat = re.compile(r'Tag: (?P<value>.*)')

        desc_file = self.package_dir / 'solutions' / desc
        with open(desc_file, 'r') as f:
            desc_content = f.read()

        # get solution file name
        if m := file_name_pat.search(desc_content):
            solution = m.group('value')
        else:
            logger.error(f'No file name found in {desc}.')
            raise ProcessError(f'No file name found in {desc}.')

        # check solution file exists
        if solution is None or not (self.package_dir / 'solutions' / solution).is_file():
            logger.error(f'The description file {desc} has error.')
            raise ProcessError(f'The description file {desc} has error.')

        # get tag
        if m := tag_pat.search(desc_content):
            tag = cast(Tag, m.group('value'))
        else:
            logger.error(f'No tag found in {desc}.')
            raise ProcessError(f'No tag found in {desc}.')

        # get expected result
        if (result := self._config['tag'].get(tag, 'rejected')) == 'rejected':
            logger.warning(f'Can not find expected result for tag {tag}, use accepted.')

        return solution, result

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
            ._archive()


def _confirm(package_dir, temp_dir, output_file, skip_confirmation=False):
    logger.info('This is Polygon2DOMjudge by cubercsl.')
    logger.info('Process Polygon Package to DOMjudge Package.')
    logger.info("Version: {}".format(__version__))

    if sys.platform.startswith('win'):
        logger.warning('It is not recommended running on windows.')

    logger.info(f'Package directory: {package_dir}')
    logger.info(f'Temp directory: {temp_dir}')
    logger.info(f'Output file: {output_file}.zip')
    if not skip_confirmation:
        input("Press enter to continue...")


class Options(TypedDict, total=False):
    force_default_validator: bool
    auto_detect_std_checker: bool
    validator_flags: ValidatorFlags
    replace_sample: bool
    hide_sample: bool
    config: Config
    memory_limit: int
    output_limit: int
    skip_confirmation: bool
    code: str  # alias of short_name


def convert_polygon_to_domjudge(
    package: StrPath, /,
    output: Optional[StrPath] = None, *,
    short_name: str = DEFAULT_CODE,
    color: str = DEFAULT_COLOR,
    **kwargs: Unpack[Options]
) -> None:
    """Convert a Polygon package to a DOMjudge package.

    Args:
        package (StrPath): The path to the polygon package directory.
        output (Optional[StrPath], optional): The path to the output DOMjudge package.
        short_name (str, optional): The short name of the problem.
        color (str, optional): The color of the problem.

    Raises:
        ProcessError: If convert failed.
        FileNotFoundError: If the package is not found.
        FileExistsError: If the output file already exists.
    """

    if kwargs.get('code'):  # code is alias of short_name
        short_name = cast(str, kwargs['code'])

    _kwargs: _Polygon2DOMjudgeArgs = {
        'replace_sample': kwargs.get('replace_sample', False),
        'hide_sample': kwargs.get('hide_sample', False),
        'auto_detect_std_checker': kwargs.get('auto_detect_std_checker', False),
        'force_default_validator': kwargs.get('force_default_validator', False),
        'validator_flags': kwargs.get('validator_flags', []),
        'config': kwargs.get('config', cast(Config, load_config(DEFAULT_CONFIG_FILE))),
    }

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
            if Path(output).is_dir():
                output_file = Path(output).resolve() / short_name
            elif Path(output).name.endswith('.zip'):
                output_file = Path(Path(output).name[:-4]).resolve()
            else:
                output_file = Path(output).resolve()
        else:
            output_file = Path.cwd() / short_name

        if Path(output_file.name + '.zip').resolve().exists():
            raise FileExistsError(errno.EEXIST, os.strerror(errno.EEXIST), f'{output_file.name}.zip')

        _confirm(package_dir, domjudge_temp_dir, output_file, skip_confirmation=skip_confirmation)

        p = Polygon2DOMjudge(package_dir, domjudge_temp_dir, output_file, short_name, color, **_kwargs)

        if kwargs.get('memory_limit'):
            p.override_memory_limit(cast(int, kwargs['memory_limit']))
        if kwargs.get('output_limit'):
            p.override_output_limit(cast(int, kwargs['output_limit']))
        p.process()


__all__ = [
    'convert_polygon_to_domjudge',
    'DEFAULT_CODE',
    'DEFAULT_COLOR',
    'DEFAULT_CONFIG_FILE',
    'Polygon2DOMjudge',
    'ProcessError',
    'Problem',
    'Test',
]
