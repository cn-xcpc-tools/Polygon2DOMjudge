import os
import logging
import re
import shutil
import xml.etree.ElementTree

import yaml

from pathlib import Path
from typing import cast, Optional, Union
from xml.etree.ElementTree import Element

from . import __version__
from .utils import ensure_dir, load_config
from .typing import Config, ValidatorFlags, _Tag

logger = logging.getLogger(__name__)

DEFAULT_ASSET_PATH = Path(__file__).resolve().parent / 'asset'
DEFAULT_TESTLIB_PATH = Path(__file__).resolve().parent / 'testlib'
DEFAULT_CONFIG_FILE = Path(os.getenv('CONFIG_PATH', DEFAULT_ASSET_PATH)) / 'config.toml'
DEFAULT_CODE = 'PROB1'
DEFAULT_COLOR = '#000000'
UNKNOWN = 'unknown'

testlib_path = (Path(os.getenv('TESTLIB_PATH', DEFAULT_TESTLIB_PATH)) / 'testlib.h').resolve()
extension_for_desc = os.getenv('EXTENSION_FOR_DESC', '.desc')


class ProcessError(RuntimeError):
    pass


class Test:
    def __init__(self, method: str, description: Optional[str] = None, cmd: Optional[str] = None, sample=False):
        self.method = method
        self.description = description
        self.cmd = cmd
        self.sample = sample

    def __str__(self):
        return f'{self.description} {"[GEN] " + self.cmd if self.cmd else ""}'.strip()


class Problem:

    _NAME_LANGUAGE_PREFERENCE = (
        'english',
        'russian',
        'chinese',
    )

    def __init__(self, problem_xml: Path, Test=Test):
        root = xml.etree.ElementTree.parse(problem_xml)
        name = self._get_preference_name(root.find('names'))

        testset = root.find('judging/testset')
        if testset is None:
            logger.error('Can not find testset in problem.xml.')
            raise ProcessError('Can not find testset in problem.xml.')

        timelimit = testset.find('time-limit')
        memorylimit = testset.find('memory-limit')
        input_path_pattern = testset.find('input-path-pattern')
        answer_path_pattern = testset.find('answer-path-pattern')

        if 'value' not in name.attrib or 'language' not in name.attrib:
            logger.error('Name is invalid in problem.xml.')
            raise ProcessError('Name is invalid in problem.xml.')

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

        self.name = name.attrib['value']
        self.language = name.attrib['language']
        self.timelimit = int(timelimit.text) / 1000.0
        self.memorylimit = int(memorylimit.text) // 1048576
        self.outputlimit = -1
        self.input_path_pattern = input_path_pattern.text
        self.answer_path_pattern = answer_path_pattern.text
        self.checker = root.find('assets/checker')
        self.interactor = root.find('assets/interactor')
        self.tests = tuple(
            Test(
                method=test.attrib['method'],
                description=test.attrib.get('description', None),
                cmd=test.attrib.get('cmd', None),
                sample=bool(test.attrib.get('sample', False))
            ) for test in testset.findall('tests/test')
        )

    def _get_preference_name(self, names: Optional[Element]):
        if names is None:
            logger.error('Can not find names in problem.xml.')
            raise ProcessError('Can not find names in problem.xml.')

        def _is_valid_name(name: Optional[Element]):
            return name is not None and 'value' in name.attrib and 'language' in name.attrib

        for lang in self._NAME_LANGUAGE_PREFERENCE:
            name = names.find(f'name[@language="{lang}"]')
            if _is_valid_name(name):
                return name

        # if no preference language found, return the first name
        name = names.find('name')
        if _is_valid_name(name):
            return name

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

    def __init__(self, package_dir: Union[str, Path], temp_dir: Union[str, Path], output_file: Union[str, Path],
                 short_name=DEFAULT_CODE,
                 color=DEFAULT_COLOR, *,
                 force_default_validator=False,
                 auto_detect_std_checker=False,
                 validator_flags=(),
                 replace_sample=False,
                 hide_sample=False,
                 config: Optional[Config] = None,
                 Problem=Problem):
        self.package_dir = Path(package_dir)
        self.short_name = short_name
        self.color = color
        self.temp_dir = Path(temp_dir)
        self.output_file = Path(output_file)

        if config is None:
            self._config: Config = load_config(DEFAULT_CONFIG_FILE)
        else:
            self._config = config

        logger.debug('Parse \'problem.xml\':')
        self._problem = Problem(self.package_dir / 'problem.xml')

        if force_default_validator and auto_detect_std_checker:
            logger.error('Can not use auto_detect_std_checker and force_default_validator at the same time.')
            raise ValueError('Can not use auto_detect_std_checker and force_default_validator at the same time.')

        self._replace_sample = replace_sample
        self._hide_sample = hide_sample or self._problem.has_interactor
        self._use_std_checker = auto_detect_std_checker and self._problem.has_std_checker or force_default_validator
        self._validator_flags: ValidatorFlags = ()

        if self._use_std_checker:
            if force_default_validator:
                self._validator_flags = validator_flags or ()
            else:
                self._validator_flags = self._config['flag'].get(self._problem.checker_name[5:], ())

    def _write_ini(self):

        logger.debug('Add \'domjudge-problem.ini\':')

        ini_file = f'{self.temp_dir}/domjudge-problem.ini'
        ini_content = (f'short-name = {self.short_name}', f'timelimit = {self._problem.timelimit}', f'color = {self.color}')
        for line in ini_content:

            logger.info(line)
        with open(ini_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(ini_content) + '\n')

        return self

    def _write_yaml(self):

        logger.debug('Add \'problem.yaml\':')

        yaml_file = self.temp_dir / 'problem.yaml'
        yaml_content = dict(name=self._problem.name)
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
                yaml_content['validator_flags'] = ' '.join(self._validator_flags)
        else:
            ensure_dir(output_validators_dir)
            if self._problem.has_interactor:

                logger.info('Use custom interactor.')
                yaml_content['validation'] = 'custom interactive'
                interactor_file = self.package_dir / self._problem.interactor_path
                ensure_dir(interactor_dir)
                shutil.copyfile(testlib_path, interactor_dir / 'testlib.h')
                shutil.copyfile(interactor_file, interactor_dir / 'interactor.cpp')
            elif self._problem.has_checker:

                logger.info('Use custom checker.')
                yaml_content['validation'] = 'custom'
                checker_file = self.package_dir / self._problem.checker_path
                ensure_dir(checker_dir)
                shutil.copyfile(testlib_path, checker_dir / 'testlib.h')
                shutil.copyfile(checker_file, checker_dir / 'checker.cpp')
            else:

                logger.error('No checker found.')
                raise ProcessError('No checker found.')

        with open(yaml_file, 'w') as f:
            yaml.dump(yaml_content, f, allow_unicode=True, default_flow_style=False)

        return self

    def _add_tests(self):

        logger.debug('Add tests:')

        ensure_dir(self.temp_dir / 'data' / 'sample')
        ensure_dir(self.temp_dir / 'data' / 'secret')
        sample_input_path_pattern = self._config['example_path_pattern']['input']
        sample_output_path_pattern = self._config['example_path_pattern']['output']

        def compare(src: Path, dst: Path):
            s, t = src.name, dst.name

            logger.debug(f'Compare {s} and {t}')
            with open(src, 'r') as f1, open(dst, 'r') as f2:
                if f1.read() != f2.read():

                    logger.warning(f'{s} and {t} are not the same, use {t}.')

        for idx, test in enumerate(self._problem.tests, 1):
            input_src = self.package_dir / (self._problem.input_path_pattern % idx)
            output_src = self.package_dir / (self._problem.answer_path_pattern % idx)

            if test.sample and not self._hide_sample:
                # interactor can not support custom sample because DOMjudge always use sample input to test
                sample_input_src = self.package_dir / 'statements' / self._problem.language / (sample_input_path_pattern % idx)
                sample_output_src = self.package_dir / 'statements' / self._problem.language / (sample_output_path_pattern % idx)
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
                self.warning(f'Output file {output_src.name} is exceed the output limit.')

            shutil.copyfile(input_src, input_dst)
            shutil.copyfile(output_src, output_dst)

            if test.__str__():
                logger.info(f'{test.__str__()}')
                with open(desc_dst, 'w', encoding='utf-8') as f:
                    f.write(test.__str__())

            return self

    def _add_jury_solutions(self):

        logger.debug('Add jury solutions:')

        ensure_dir(self.temp_dir / 'submissions' / 'accepted')
        ensure_dir(self.temp_dir / 'submissions' / 'wrong_answer')
        ensure_dir(self.temp_dir / 'submissions' / 'time_limit_exceeded')
        ensure_dir(self.temp_dir / 'submissions' / 'run_time_error')

        for desc in filter(lambda x: x.name.endswith(extension_for_desc), (self.package_dir / 'solutions').iterdir()):
            solution, result = self._get_submission_and_result(desc)
            src = self.package_dir / 'solutions' / solution
            dst = self.temp_dir / 'submissions' / result / solution
            logger.info(f'- {solution} (Expected Result: {result})')
            shutil.copyfile(src, dst)

        return self

    def _archive(self):
        shutil.make_archive(self.output_file, 'zip', self.temp_dir, logger=logger)
        logger.info(f'Make package {self.output_file.name}.zip success.')
        return self

    def _get_submission_and_result(self, desc: Path):
        solution: Optional[str] = None
        tag: _Tag | None = None

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
            tag = cast(_Tag, m.group('value'))
        else:
            logger.error(f'No tag found in {desc}.')
            raise ProcessError(f'No tag found in {desc}.')

        # get expected result
        if (result := self._config['tag'].get(tag)) is None:
            result = 'accepted'
            logger.warning(f'Can not find expected result for tag {tag}, use accepted.')

        return solution, result

    def override_memory_limit(self, memory_limit: int):
        if self._problem.memorylimit == memory_limit:
            return self
        logger.info(f'Override memory limit: {memory_limit}')
        self._problem.memorylimit = memory_limit
        return self

    def override_output_limit(self, output_limit: int):
        if self._problem.outputlimit == output_limit:
            return self
        logger.info(f'Override output limit: {output_limit}')
        self._problem.outputlimit = output_limit
        return self

    def process(self):
        return self._write_ini() \
            ._write_yaml() \
            ._add_tests() \
            ._add_jury_solutions() \
            ._archive()


__all__ = ['Polygon2DOMjudge', 'ProcessError', 'Problem', 'Test']
