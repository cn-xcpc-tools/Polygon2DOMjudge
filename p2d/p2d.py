import argparse
import json
import logging
import os
import shutil
import sys
import tempfile
import time
import traceback
import xml.etree.ElementTree


config = {}
START_OF_SUBPROCESS = '=' * 50
DEFAULT_CONFIG_PATH = os.path.dirname(os.path.realpath(__file__))
DEFAULT_TESTLIB_PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
DEFAULT_PROBID = 'PROB1'
DEFAULT_COLOR = '#000000'

testlib = os.path.join(os.getenv('TESTLIB_PATH', DEFAULT_TESTLIB_PATH), 'testlib.h')
extention_for_desc = os.getenv('EXTENTION_FOR_DESC', '.desc')


def format_exception(grep_word):
    exception_list = traceback.format_stack()
    exception_list = exception_list[:-2]
    exception_list.extend(traceback.format_tb(sys.exc_info()[2]))
    exception_list.extend(traceback.format_exception_only(
        sys.exc_info()[0], sys.exc_info()[1]))
    filtered = []
    for m in exception_list:
        if str(grep_word) in m:
            filtered.append(m)

    exception_str = "Traceback (most recent call last):\n"
    exception_str += "".join(filtered)
    # Removing the last \n
    exception_str = exception_str[:-1]
    return exception_str


config_file = os.path.join(os.getenv('CONFIG_PATH', DEFAULT_CONFIG_PATH), 'config.json')
try:
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
except FileNotFoundError:
    print('\'config.json\' not found!')
except json.JSONDecodeError as e:
    print(format_exception(e))
    exit(1)


def ensure_dir(s):
    if not os.path.exists(s):
        os.makedirs(s)


def ensure_no_dir(s):
    if os.path.exists(s):
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
            logger.error(msg)
        raise ProcessError(msg)

    def __init__(self, package_dir, temp_dir, output_file,
                 probid=DEFAULT_PROBID, color=DEFAULT_COLOR, validator_flags=[],
                 logger=None):
        self.logger = logger

        self.package_dir = package_dir
        self.probid = probid
        self.color = color
        self.validator_flags = validator_flags
        self.temp_dir = temp_dir
        self.output_file = output_file

        self.debug('Parse \'problem.xml\':')
        xml_file = f'{package_dir}/problem.xml'
        root = xml.etree.ElementTree.parse(xml_file)
        judging = root.find('judging')
        testset = judging.find('testset')

        self.name = root.find('names').find('name').attrib['value']
        self.timelimit = int(testset.find('time-limit').text) / 1000.0
        self.memlimit = int(testset.find('memory-limit').text) // 1048576
        self.checker = root.find('assets').find('checker')
        self.interactor = root.find('assets').find('interactor')
        self.input_path_pattern = testset.find('input-path-pattern').text
        self.answer_path_pattern = testset.find('answer-path-pattern').text
        self.tests = []
        for test in testset.find('tests').findall('test'):
            method = test.attrib['method']
            description = test.attrib.get('description', None)
            cmd = test.attrib.get('cmd', None)
            sample = bool(test.attrib.get('sample', False))
            self.tests.append(self.Test(method, description, cmd, sample))

    def _write_ini(self):
        self.debug('Add \'domjudge-problem.ini\':')
        ini_file = f'{self.temp_dir}/domjudge-problem.ini'
        ini_content = [
            f'probid = {self.probid}',
            f'timelimit = {self.timelimit}',
            f'color = {self.color}'
        ]
        for line in ini_content:
            self.info(line)
        with open(ini_file, 'w', encoding='utf-8') as f:
            f.writelines(map(lambda s: s + '\n', ini_content))

    def _write_yaml(self):
        self.debug('Add \'problem.yaml\':')

        yaml_file = f'{self.temp_dir}/problem.yaml'
        name = self.name.replace('"', r'\"')
        yaml_content = f'name: "{name}"\nlimits:\n  memory: {self.memlimit}\n'

        self.info(yaml_content[:-1])

        checker_name = self.checker.attrib.get('name', 'unkown')
        validator_flags = []
        if '__auto' in self.validator_flags and checker_name.startswith('std::'):
            validator_flags = config['flag'].get(checker_name.lstrip('std::'), [])
        if '__default' in self.validator_flags:
            validator_flags = list(filter(lambda x: not x.startswith('__'), self.validator_flags))

        yaml_file = f'{self.temp_dir}/problem.yaml'
        output_validators_dir = f'{self.temp_dir}/output_validators'
        checker_dir = f'{output_validators_dir}/checker'
        interactor_dir = f'{output_validators_dir}/interactor'

        if self.interactor is None and '__auto' in self.validator_flags or '__default' in self.validator_flags:
            # can not support both interactor and checker
            self.info(f'Use std checker: {checker_name}')
            with open(yaml_file, 'w', encoding='utf-8') as f:
                f.write(yaml_content)
                f.write('validation: default\n')
                if validator_flags:
                    self.info(f'Validator flags: {" ".join(validator_flags)}')
                    f.write(f'validator_flags: {" ".join(validator_flags)}\n')
        else:
            ensure_dir(output_validators_dir)
            if self.interactor is not None:
                self.info('Use custom interactor.')
                with open(yaml_file, 'w', encoding='utf-8') as f:
                    f.write(yaml_content)
                    f.write('validation: custom interactive\n')
                ensure_dir(interactor_dir)
                shutil.copyfile(testlib, f'{interactor_dir}/testlib.h')
                interactor_path = self.interactor.find('source').attrib['path']
                interactor_file = f'{self.package_dir}/{interactor_path}'
                shutil.copyfile(interactor_file, f'{interactor_dir}/interactor.cpp')
            elif self.checker is not None:
                self.info('Use custom checker.')
                with open(yaml_file, 'w', encoding='utf-8') as f:
                    f.write(yaml_content)
                    f.write('validation: custom\n')
                ensure_dir(checker_dir)
                shutil.copyfile(testlib, f'{checker_dir}/testlib.h')
                checker_path = self.checker.find('source').attrib['path']
                checker_file = f'{self.package_dir}/{checker_path}'
                shutil.copyfile(checker_file, f'{checker_dir}/checker.cpp')
            else:
                self.error('No checker found.')

    def _add_tests(self):
        self.debug('Add tests:')
        ensure_dir(f'{self.temp_dir}/data')
        ensure_dir(f'{self.temp_dir}/data/sample')
        ensure_dir(f'{self.temp_dir}/data/secret')

        for idx, test in enumerate(self.tests, 1):

            input_src = f'{self.package_dir}/{self.input_path_pattern % idx}'
            output_src = f'{self.package_dir}/{self.answer_path_pattern % idx}'
            if test.sample:
                input_dst = f'{self.temp_dir}/data/sample/{"%02d" % idx}.in'
                output_dst = f'{self.temp_dir}/data/sample/{"%02d" % idx}.ans'
                desc_dst = f'{self.temp_dir}/data/sample/{"%02d" % idx}.desc'
                self.info(f'* sample: {"%02d" % idx}.(in/ans) {test.method}')
            else:
                input_dst = f'{self.temp_dir}/data/secret/{"%02d" % idx}.in'
                output_dst = f'{self.temp_dir}/data/secret/{"%02d" % idx}.ans'
                desc_dst = f'{self.temp_dir}/data/secret/{"%02d" % idx}.desc'
                self.info(f'* secret: {"%02d" % idx}.(in/ans) {test.method}')

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

    def _add_jury_solutions(self):
        self.debug('Add jury solutions:')
        ensure_dir(f'{self.temp_dir}/submissions')
        ensure_dir(f'{self.temp_dir}/submissions/accepted')
        ensure_dir(f'{self.temp_dir}/submissions/wrong_answer')
        ensure_dir(f'{self.temp_dir}/submissions/time_limit_exceeded')
        ensure_dir(f'{self.temp_dir}/submissions/run_time_error')

        def get_solution(desc):
            result = {}
            desc_file = f'{self.package_dir}/solutions/{desc}'
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

        for desc in filter(lambda x: x.endswith(extention_for_desc), os.listdir(f'{self.package_dir}/solutions')):
            solution, result = get_solution(desc)
            src = f'{self.package_dir}/solutions/{solution}'
            dst = f'{self.temp_dir}/submissions/{result}/{solution}'
            self.info(f'- {solution} (Expected Result: {result})')
            shutil.copyfile(src, dst)

    def _archive(self):
        shutil.make_archive(self.output_file, 'zip', self.temp_dir, logger=self.logger)
        self.info(f'Make package {os.path.basename(self.output_file)}.zip success.')

    def process(self):
        subprocess = [
            self._write_ini,
            self._write_yaml,
            self._add_tests,
            self._add_jury_solutions,
            self._archive
        ]
        for func in subprocess:
            self.info(START_OF_SUBPROCESS)
            func()


def main(args):

    def print_info(package_dir, temp_dir, output_file):
        logger.info('This is p2d.py by cubercsl.')
        logger.info('Process Polygon Package to Domjudge Package.')

        if sys.platform.startswith('win'):
            logger.warning('It is not recommended running on windows.')

        logger.info(f'Package directory: {package_dir}')
        logger.info(f'Temp directory: {temp_dir}')
        logger.info(f'Output file: {output_file}.zip')
        input("Press enter to continue...")

    package_dir = os.path.realpath(args.package)
    output_file = os.path.join(os.getcwd(), os.path.basename(package_dir))

    probid = args.code if args.code else DEFAULT_PROBID
    color = args.color if args.color else DEFAULT_COLOR

    if args.output:
        if os.path.isdir(args.output):
            output_file = os.path.join(os.path.abspath(args.output), os.path.basename(package_dir))
        else:
            output_file = os.path.abspath(args.output.rstrip('.zip'))

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

    with tempfile.TemporaryDirectory() as temp_dir:
        print_info(package_dir, temp_dir, output_file)
        try:
            Polygon2Domjudge(package_dir, temp_dir, output_file,
                             probid, color, validator_flags, logger).process()
        except Exception as e:
            logger.error(format_exception(e))
            sys.exit(1)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Process Polygon Package to Domjudge Package.')
    parser.add_argument('package', type=str, help='path of the polygon package')
    parser.add_argument('--code', type=str, help='problem code for domjudge')
    parser.add_argument('--color', type=str, help='problem color for domjudge (in RRGGBB format)')
    parser.add_argument('-l', '--log_level', default='info',
                        help='set log level (debug, info, warning, error, critical)')
    parser.add_argument('-o', '--output', type=str, help='path of the output package')
    parser.add_argument('--default', action='store_true', help='use default validation')
    parser.add_argument('--auto', action='store_true', help='use default validation it can be replaced by the default one')
    parser.add_argument('--case_sensitive', action='store_true', help='case_sensitive flag')
    parser.add_argument('--space_change_sensitive', action='store_true', help='space_change_sensitive flag')
    parser.add_argument('--float_relative_tolerance', type=str, help='float_relative_tolerance flag')
    parser.add_argument('--float_absolute_tolerance', type=str, help='float_absolute_tolerance flag')
    parser.add_argument('--float_tolerance', type=str, help='float_tolerance flag')
    args = parser.parse_args()

    log_path = os.getenv('LOG_PATH', os.path.join(os.getcwd(), 'log'))
    ensure_dir(log_path)
    logger = logging.getLogger(__name__)
    logger.setLevel(eval("logging." + args.log_level.upper()))
    handler = logging.FileHandler(f'{log_path}/{time.strftime("%Y%m%d-%H%M%S", time.localtime(time.time()))}.log')
    console = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(console)
    logger.addHandler(handler)

    main(args)
