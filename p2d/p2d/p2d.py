#! /usr/bin/env python3

import argparse
import json
import logging
import os
import shutil
import sys
import tempfile
import traceback
import xml.etree.ElementTree

try:
    import yaml
except ImportError:
    print('Can not import yaml, please install PyYaml first via pip or package manager of your distribution.')
    sys.exit(1)

from pathlib import Path
from typing import Tuple, Dict


config = {}
START_OF_SUBPROCESS = '=' * 50
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent
DEFAULT_TESTLIB_PATH = Path(__file__).resolve().parent / 'asset'
DEFAULT_PROBID = 'PROB1'
DEFAULT_COLOR = '#000000'

testlib_path = (Path(os.getenv('TESTLIB_PATH', DEFAULT_TESTLIB_PATH)) / 'testlib.h').resolve()
extention_for_desc = os.getenv('EXTENTION_FOR_DESC', '.desc')


def format_exception(e: Exception):
    return ''.join(traceback.format_exception(type(e), e, e.__traceback__))


config_file = Path(os.getenv('CONFIG_PATH', DEFAULT_CONFIG_PATH)) / 'config.json'
try:
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
except FileNotFoundError:
    print('\'config.json\' not found!')
except json.JSONDecodeError as e:
    print(format_exception(e))
    exit(1)


def ensure_dir(s: Path):
    if not s.exists():
        s.mkdir(parents=True)


def ensure_no_dir(s: Path):
    if s.exists():
        shutil.rmtree(s)


class ProcessError(Exception):
    pass


class Polygon2Domjudge:
    class Test:
        def __init__(self, method, description=None, cmd=None, sample=False):
            self.method = method
            self.description = description
            self.cmd = cmd
            self.sample = sample

    def debug(self, msg):
        if self.logger is not None:
            self.logger.debug(msg)

    def info(self, msg):
        if self.logger is not None:
            self.logger.info(msg)

    def warning(self, msg):
        if self.logger is not None:
            self.logger.warning(msg)

    def error(self, msg):
        if self.logger is not None:
            self.logger.error(msg)
        raise ProcessError(msg)

    def __init__(self, package_dir: str | Path, temp_dir: str | Path, output_file: str | Path,
                 short_name=DEFAULT_PROBID, color=DEFAULT_COLOR,
                 validator_flags=(),
                 logger=None) -> None:
        self.logger = logger

        self.package_dir = Path(package_dir)
        self.short_name = short_name
        self.color = color
        self.validator_flags = validator_flags
        self.temp_dir = Path(temp_dir)
        self.output_file = Path(output_file)

        self.debug('Parse \'problem.xml\':')
        xml_file = f'{package_dir}/problem.xml'
        root = xml.etree.ElementTree.parse(xml_file)
        testset = root.find('judging/testset')
        name = root.find('names/name[@language="english"]')
        if name is None:
            self.warning('No english name found.')
            name = root.find('names/name')
        self.language = name.attrib['language']
        self.name = name.attrib['value']
        self.timelimit = int(testset.find('time-limit').text) / 1000.0
        self.memorylimit = int(testset.find('memory-limit').text) // 1048576
        self.outputlimit = -1
        self.checker = root.find('assets/checker')
        self.interactor = root.find('assets/interactor')
        self.input_path_pattern = testset.find('input-path-pattern').text
        self.answer_path_pattern = testset.find('answer-path-pattern').text
        self.tests = []
        for test in testset.findall('tests/test'):
            method = test.attrib['method']
            description = test.attrib.get('description', None)
            cmd = test.attrib.get('cmd', None)
            sample = bool(test.attrib.get('sample', False))
            self.tests.append(self.Test(method, description, cmd, sample))

    def _write_ini(self) -> None:
        self.debug('Add \'domjudge-problem.ini\':')
        ini_file = f'{self.temp_dir}/domjudge-problem.ini'
        ini_content = f'short-name = {self.short_name}\ntimelimit = {self.timelimit}\ncolor = {self.color}'
        self.info(ini_content)
        with open(ini_file, 'w', encoding='utf-8') as f:
            f.write(ini_content)

    def _write_yaml(self) -> None:
        self.debug('Add \'problem.yaml\':')

        yaml_file = self.temp_dir / 'problem.yaml'
        yaml_content = dict(name=self.name)
        if self.memorylimit > 0 or self.outputlimit > 0:
            yaml_content['limits'] = {}
            if self.memorylimit > 0:
                yaml_content['limits']['memory'] = self.memorylimit
            if self.outputlimit > 0:
                yaml_content['limits']['output'] = self.outputlimit

        checker_name = self.checker.attrib.get('name', 'unknown')
        if '__auto' in self.validator_flags and checker_name.startswith('std::'):
            validator_flags = config['flag'].get(checker_name.lstrip('std::'), ())
        if '__default' in self.validator_flags:
            validator_flags = tuple(filter(lambda x: not x.startswith('__'), self.validator_flags))

        yaml_file = self.temp_dir / 'problem.yaml'
        output_validators_dir = self.temp_dir / 'output_validators'
        checker_dir = output_validators_dir / 'checker'
        interactor_dir = output_validators_dir / 'interactor'

        if self.interactor is None and ('__auto' in self.validator_flags and checker_name.startswith('std::') or '__default' in self.validator_flags):
            # can not support both interactor and checker
            self.info(f'Use std checker: {checker_name}')
            yaml_content['validation'] = 'default'
            if validator_flags:
                yaml_content['validator_flags'] = ' '.join(validator_flags)
        else:
            ensure_dir(output_validators_dir)
            if self.interactor is not None:
                self.info('Use custom interactor.')
                yaml_content['validation'] = 'custom interactive'
                ensure_dir(interactor_dir)
                shutil.copyfile(testlib_path, interactor_dir / 'testlib.h')
                interactor_path = self.interactor.find('source').attrib['path']
                interactor_file = self.package_dir / interactor_path
                shutil.copyfile(interactor_file, interactor_dir / 'interactor.cpp')
            elif self.checker is not None:
                self.info('Use custom checker.')
                yaml_content['validation'] = 'custom'
                ensure_dir(checker_dir)
                shutil.copyfile(testlib_path, checker_dir / 'testlib.h')
                checker_path = self.checker.find('source').attrib['path']
                checker_file = self.package_dir / checker_path
                shutil.copyfile(checker_file, checker_dir / 'checker.cpp')
            else:
                self.error('No checker found.')

        with open(yaml_file, 'w') as f:
            yaml.dump(yaml_content, f, allow_unicode=True, default_flow_style=False)

    def _add_tests(self) -> None:
        self.debug('Add tests:')
        ensure_dir(self.temp_dir / 'data' / 'sample')
        ensure_dir(self.temp_dir / 'data' / 'secret')
        sample_input_path_pattern = config['example_path_pattern']['input']
        sample_output_path_pattern = config['example_path_pattern']['output']

        def compare(src: Path, dst: Path):
            s, t = src.name, dst.name
            self.debug(f'Compare {s} and {t}')
            with open(src, 'r') as f1, open(dst, 'r') as f2:
                if f1.read() != f2.read():
                    self.warning(f'{s} and {t} are not the same, use {t}.')

        for idx, test in enumerate(self.tests, 1):

            input_src = self.package_dir / (self.input_path_pattern % idx)
            output_src = self.package_dir / (self.answer_path_pattern % idx)
            if test.sample and self.interactor is None:
                # interactor can not support custom sample because DOMjudge always use sample input to test
                sample_input_src = self.package_dir / 'statements' / self.language / (sample_input_path_pattern % idx)
                sample_output_src = self.package_dir / 'statements' / self.language / (sample_output_path_pattern % idx)
                if sample_input_src.exists():
                    compare(input_src, sample_input_src)
                    input_src = sample_input_src
                if sample_output_src.exists():
                    compare(output_src, sample_output_src)
                    output_src = sample_output_src
                input_dst = self.temp_dir / 'data' / 'sample' / f'{"%02d" % idx}.in'
                output_dst = self.temp_dir / 'data' / 'sample' / f'{"%02d" % idx}.ans'
                desc_dst = self.temp_dir / 'data' / 'sample' / f'{"%02d" % idx}.desc'
                self.info(f'* sample: {"%02d" % idx}.(in/ans) {test.method}')
            else:
                input_dst = self.temp_dir / 'data' / 'secret' / f'{"%02d" % idx}.in'
                output_dst = self.temp_dir / 'data' / 'secret' / f'{"%02d" % idx}.ans'
                desc_dst = self.temp_dir / 'data' / 'secret' / f'{"%02d" % idx}.desc'
                self.info(f'* secret: {"%02d" % idx}.(in/ans) {test.method}')
            if self.outputlimit > 0 and output_src.stat().st_size > self.outputlimit * 1048576:
                self.warning(f'Output file {output_src.name} is exceed the output limit.')

            shutil.copyfile(input_src, input_dst)
            shutil.copyfile(output_src, output_dst)

            desc = []
            if test.description is not None:
                self.info(test.description)
                desc.append(test.description)

            if test.cmd is not None:
                self.info(f'[GEN] {test.cmd}')
                desc.append(f'[GEN] {test.cmd}')

            if desc:
                with open(desc_dst, 'w', encoding='utf-8') as f:
                    f.write(f'{" ".join(desc)}\n')

    def _add_jury_solutions(self) -> None:
        self.debug('Add jury solutions:')
        ensure_dir(self.temp_dir / 'submissions' / 'accepted')
        ensure_dir(self.temp_dir / 'submissions' / 'wrong_answer')
        ensure_dir(self.temp_dir / 'submissions' / 'time_limit_exceeded')
        ensure_dir(self.temp_dir / 'submissions' / 'run_time_error')

        def get_solution(desc: str | Path) -> Tuple[str, str]:
            result: Dict[str, str] = {}
            desc_file = self.package_dir / 'solutions' / desc
            with open(desc_file, 'r', encoding='utf-8') as f:
                for line in f.readlines():
                    key, value = line.strip().split(': ', maxsplit=2)
                    if key == 'File name':
                        result[key] = value
                    elif key == 'Tag':
                        try:
                            if value not in config['tag'].keys():
                                self.error(f'Unknown tag: {value}')
                            result[key] = config['tag'][value]
                        except KeyError:
                            self.warning(f'Treat unknown tag \'{value}\' as \'accepted\'.')
                            result[key] = 'accepted'
            if not ('File name' in result.keys() and 'Tag' in result.keys()):
                self.error(f'The description file {desc} has error.')
            return result['File name'], result['Tag']

        for desc in filter(lambda x: x.name.endswith(extention_for_desc), (self.package_dir / 'solutions').iterdir()):
            solution, result = get_solution(desc)
            src = self.package_dir / 'solutions' / solution
            dst = self.temp_dir / 'submissions' / result / solution
            self.info(f'- {solution} (Expected Result: {result})')
            shutil.copyfile(src, dst)

    def _archive(self):
        shutil.make_archive(self.output_file, 'zip', self.temp_dir, logger=self.logger)
        self.info(f'Make package {self.output_file.name}.zip success.')

    def process(self):
        subprocess = (
            self._write_ini,
            self._write_yaml,
            self._add_tests,
            self._add_jury_solutions,
            self._archive
        )
        for func in subprocess:
            self.info(START_OF_SUBPROCESS)
            func()


def main():
    parser = argparse.ArgumentParser(description='Process Polygon Package to Domjudge Package.')
    parser.add_argument('package', type=Path, help='path of the polygon package')
    parser.add_argument('--code', type=str, help='problem code for domjudge')
    parser.add_argument('--color', type=str, help='problem color for domjudge (in RRGGBB format)')
    parser.add_argument('-l', '--log_level', default='info',
                        help='set log level (debug, info, warning, error, critical)')
    parser.add_argument('-o', '--output', type=Path, help='path of the output package')
    parser.add_argument('--default', action='store_true', help='use default validation')
    parser.add_argument('--auto', action='store_true', help='use default validation it can be replaced by the default one')
    parser.add_argument('--case_sensitive', action='store_true', help='case_sensitive flag')
    parser.add_argument('--space_change_sensitive', action='store_true', help='space_change_sensitive flag')
    parser.add_argument('--float_relative_tolerance', type=str, help='float_relative_tolerance flag')
    parser.add_argument('--float_absolute_tolerance', type=str, help='float_absolute_tolerance flag')
    parser.add_argument('--float_tolerance', type=str, help='float_tolerance flag')
    parser.add_argument('--memory_limit', type=int, help='memory limit override for domjudge (in MB), -1 means use domjudge default')  # default use polygon default
    parser.add_argument('--output_limit', type=int, help='output limit override for domjudge (in MB), -1 means use domjudge default', default=-1)
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level.upper(), None),
                        format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    def print_info(package_dir, temp_dir, output_file):
        logger.info('This is p2d.py by cubercsl.')
        logger.info('Process Polygon Package to Domjudge Package.')

        if sys.platform.startswith('win'):
            logger.warning('It is not recommended running on windows.')

        logger.info(f'Package directory: {package_dir}')
        logger.info(f'Temp directory: {temp_dir}')
        logger.info(f'Output file: {output_file}.zip')
        input("Press enter to continue...")

    package_dir = Path(args.package).resolve()
    output_file = Path.cwd() / package_dir.name
    short_name = args.code if args.code else DEFAULT_PROBID
    color = args.color if args.color else DEFAULT_COLOR

    if args.output:
        if Path(args.output).is_dir():
            output_file = Path(args.output).resolve() / package_dir.name
        else:
            output_file = Path(args.output.name.rstrip('.zip')).resolve()

    validator_flags = []

    if args.default:
        validator_flags = ['__default']
        if args.case_sensitive:
            validator_flags.append('case_sensitive')
        if args.space_change_sensitive:
            validator_flags.append('space_change_sensitive')
        if args.float_relative_tolerance:
            validator_flags.append('float_relative_tolerance')
            validator_flags.append(args.float_relative_tolerance)
        if args.float_absolute_tolerance:
            validator_flags.append('float_absolute_tolerance')
            validator_flags.append(args.float_absolute_tolerance)
        if args.float_tolerance:
            validator_flags.append('float_tolerance')
            validator_flags.append(args.float_tolerance)

    if args.auto:
        validator_flags = ['__auto']

    with tempfile.TemporaryDirectory(prefix='p2d-domjudge') as temp_dir:
        print_info(package_dir, temp_dir, output_file)
        try:
            problem = Polygon2Domjudge(package_dir, temp_dir, output_file,
                                       short_name, color, tuple(validator_flags), logger)
            # memory_limit and output_limit can be override by command line
            if args.memory_limit:
                problem.memorylimit = args.memory_limit
            if args.output_limit:
                problem.outputlimit = args.output_limit
            problem.process()
        except Exception as e:
            logger.error(format_exception(e))
            sys.exit(1)


if __name__ == '__main__':
    main()
