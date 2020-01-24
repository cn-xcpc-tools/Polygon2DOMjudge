#!/usr/bin/env python
import argparse
import json
import logging
import hashlib
import math
import os
import sys
import xml.etree.ElementTree
from shutil import copyfile, rmtree, make_archive
from time import strftime, localtime, time

config = {}
END_OF_SUBPROCESS = '=' * 50


def ensure_dir(s):
    if not os.path.exists(s):
        os.makedirs(s)


def ensure_no_dir(s):
    if os.path.exists(s):
        rmtree(s)


def main(args):

    def start(package_dir, output_dir, output_file):
        logger.info('This is p2d.py by cubercsl.')
        logger.info('Process Polygon Package to Domjudge Package.')
        logger.info('Package directory: {}'.format(package_dir))
        logger.info('Temp directory: {}'.format(output_dir))
        logger.info('Output file: {}.zip'.format(output_file))
        input("Press enter to continue...")
        logger.info(END_OF_SUBPROCESS)

    def parse_problem():
        logger.info('Parse \'problem.xml\':')
        xml_file = '{}/problem.xml'.format(package_dir)
        root = xml.etree.ElementTree.parse(xml_file)
        name = root.find('names').find('name').attrib['value']
        timelimit = float(math.ceil(float(root.find('judging').find('testset').find('time-limit').text) / 1000.0))
        checker = root.find('assets').find('checker')
        interactor = root.find('assets').find('interactor')
        logger.info('Problem Name: {}'.format(name))
        logger.info('Time Limit: {}'.format(timelimit))
        logger.info(END_OF_SUBPROCESS)
        return name, timelimit, checker, interactor

    def write_ini(probid, name, timelimit, color):
        logger.info('Add \'domjudge-problem.ini\':')
        ini_file = '{}/domjudge-problem.ini'.format(output_dir)
        ini_content = [
            'probid = {}'.format(probid),
            'name = {}'.format(name.replace("'", "`")),
            'timelimit = {}'.format(timelimit),
            'color = {}'.format(color)
        ]
        [*map(logger.info, ini_content)]
        with open(ini_file, 'w', encoding='utf-8') as f:
            f.writelines(map(lambda s: s + '\n', ini_content))
        logger.info(END_OF_SUBPROCESS)

    def add_output_validator():
        logger.info('Add output validator:')

        def get_checker_md5(checker):
            if checker is None:
                return None
            checker_source = checker.find('source')
            checker_file = '{}/{}'.format(package_dir, checker_source.attrib['path'])
            with open(checker_file, 'r', encoding='utf-8') as f:
                file_md5 = hashlib.md5(f.read().replace('\r\n', '\n').encode('utf-8'))
            return file_md5.hexdigest().lower()

        checker_md5 = get_checker_md5(checker)
        logger.info('Checker md5: {}'.format(checker_md5))
        validator_flags = []
        try:
            if checker_md5 in config['checker'].keys():
                args.default = True
                checker_name = config['checker'][checker_md5]
                logger.info('Use std checker: std::{}'.format(checker_name))
                validator_flags = config['flag'].get(checker_name)
        except KeyError:
            pass

        yaml_file = '{}/problem.yaml'.format(output_dir)
        output_validators_dir = '{}/output_validators'.format(output_dir)
        checker_dir = '{}/checker'.format(output_validators_dir)
        interactor_dir = '{}/interactor'.format(output_validators_dir)
        if args.default:
            with open(yaml_file, 'w', encoding='utf-8') as f:
                f.write('validation: default\n')
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
                if validator_flags:
                    logger.info('Validator flags: {}'.format(' '.join(validator_flags)))
                    f.write('validator_flags: {}\n'.format(' '.join(validator_flags)))
        else:
            ensure_dir(output_validators_dir)
            if interactor is not None:
                logger.info('Use custom interactor.')
                with open(yaml_file, 'w', encoding='utf-8') as f:
                    f.write('validation: custom interactive\n')
                ensure_dir(interactor_dir)
                copyfile(testlib, '{}/testlib.h'.format(interactor_dir))
                interactor_file = '{}/{}'.format(package_dir, interactor.find('source').attrib['path'])
                copyfile(interactor_file, '{}/interactor.cpp'.format(interactor_dir))
            elif checker is not None:
                logger.info('Use custom checker.')
                with open(yaml_file, 'w', encoding='utf-8') as f:
                    f.write('validation: custom\n')
                ensure_dir(checker_dir)
                copyfile(testlib, '{}/testlib.h'.format(checker_dir))
                checker_file = '{}/{}'.format(package_dir, checker.find('source').attrib['path'])
                copyfile(checker_file, '{}/checker.cpp'.format(checker_dir))
            else:
                raise Exception('No checker found.')
        logger.info(END_OF_SUBPROCESS)

    def add_test():
        logger.info('Add tests:')
        ensure_dir('{}/data'.format(output_dir))
        ensure_dir('{}/data/sample'.format(output_dir))
        ensure_dir('{}/data/secret'.format(output_dir))

        for test in filter(lambda x: not x.endswith(extention_for_output), os.listdir('{}/tests'.format(package_dir))):
            input_src = '{}/tests/{}'.format(package_dir, test)
            output_src = '{}/tests/{}{}'.format(package_dir, test, extention_for_output)
            if test in samples:
                input_dst = '{}/data/sample/{}.in'.format(output_dir, test)
                output_dst = '{}/data/sample/{}.ans'.format(output_dir, test)
                logger.info('* sample: {}.(in/ans)'.format(test))
            else:
                input_dst = '{}/data/secret/{}.in'.format(output_dir, test)
                output_dst = '{}/data/secret/{}.ans'.format(output_dir, test)
                logger.info('* secret: {}.(in/ans)'.format(test))
            copyfile(input_src, input_dst)
            copyfile(output_src, output_dst)
        logger.info(END_OF_SUBPROCESS)

    def add_jury_solution():
        logger.info('Add jury solutions:')
        ensure_dir('{}/submissions'.format(output_dir))
        ensure_dir('{}/submissions/accepted'.format(output_dir))
        ensure_dir('{}/submissions/wrong_answer'.format(output_dir))
        ensure_dir('{}/submissions/time_limit_exceeded'.format(output_dir))
        ensure_dir('{}/submissions/run_time_error'.format(output_dir))

        def get_solution(desc):
            result = {}
            desc_file = '{}/solutions/{}'.format(package_dir, desc)
            with open(desc_file, 'r', encoding='utf-8') as f:
                for _ in f.readlines():
                    key, value = _.strip().split(': ', maxsplit=2)
                    if key == 'File name':
                        result[key] = value
                    elif key == 'Tag':
                        try:
                            if value not in config['tag'].keys():
                                raise Exception('Unknown tag: {}'.format(value))
                            result[key] = config['tag'][value]
                        except KeyError:
                            logger.warning('Treat unknown tag \'{}\' as \'accepted\'.'.format(value))
                            result[key] = 'accepted'
            if not ('File name' in result.keys() or 'Tag' in result.keys()):
                raise Exception('The description file {} has error.'.format(desc))
            return result['File name'], result['Tag']

        for desc in filter(lambda x: x.endswith(extention_for_desc), os.listdir('{}/solutions'.format(package_dir))):
            solution, result = get_solution(desc)
            src = '{}/solutions/{}'.format(package_dir, solution)
            dst = '{}/submissions/{}/{}'.format(output_dir, result, solution)
            copyfile(src, dst)
            logger.info('- {} (Expected Result: {})'.format(solution, result))
        logger.info(END_OF_SUBPROCESS)

    testlib = (os.getenv('TESTLIB_PATH') or '..').strip('/') + '/testlib.h'
    output_dir = (os.getenv('TMP_DIR') or 'tmp').strip('/')
    extention_for_output = os.getenv('EXTENTION_FOR_OUTPUT') or '.a'
    extention_for_desc = os.getenv('EXTENTION_FOR_DESC') or '.desc'
    probid = 'PROB1'
    color = '#000000'
    samples = ['01']
    package_dir = args.package.strip('/')
    output_file = args.package.strip('/')
    if args.code: probid = args.code
    if args.color: color = args.color
    if args.sample: samples = [args.sample]
    if args.num_samples:
        assert len(samples) == 1
        first = int(samples[0])
        num_samples = int(args.num_samples)
        assert (num_samples < 100)
        samples = ['{0:02d}'.format(i) for i in range(first, first + num_samples)]
    if args.output:
        output_file = args.output
        if output_file.endswith('/'): output_file = output_file + package_dir.split('/')[-1]
        if output_file.endswith('.zip'): output_file = output_file[:-4]
        if output_file.startswith('./'): output_file = output_file[2:]

    start(package_dir, output_dir, output_file)

    ensure_no_dir(output_dir)
    ensure_dir(output_dir)

    try:
        name, timelimit, checker, interactor = parse_problem()
        write_ini(probid, name, timelimit, color)
        add_output_validator()
        add_test()
        add_jury_solution()
        make_archive(output_file, 'zip', output_dir)
        ensure_no_dir(output_dir)
        logger.info('Make package {}.zip success.'.format(output_file.split('/')[-1]))
    except Exception as e:
        logger.error(e)


ensure_dir('log')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler('log/{}.log'.format(strftime('%Y-%m-%d %H:%M:%S', localtime(time()))))
console = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(console)
logger.addHandler(handler)

try:
    with open(os.getenv('CONFIG_PATH') or 'config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
except FileNotFoundError:
    logger.warning('\'config.json\' not found!')
except json.JSONDecodeError as e:
    logger.error(e)
    exit()

parser = argparse.ArgumentParser(description='Process Polygon Package to Domjudge Package.')
parser.add_argument('package', type=str, help='path of the polygon package')
parser.add_argument('--code', type=str, help='problem code for domjudge')
parser.add_argument('--sample', type=str, help='Specify the filename for sample test. Defaults to \'01\'')
parser.add_argument('--num-samples', type=str, help='Specify the number of sample test cases. Defaults to \'1\'')
parser.add_argument('--color', type=str, help='problem color for domjudge (in RRGGBB format)')
parser.add_argument('-o', '--output', type=str, help='path of the output package')
parser.add_argument('--default', action='store_true', help='use default validation')
parser.add_argument('--case_sensitive', action='store_true', help='case_sensitive flag')
parser.add_argument('--space_change_sensitive', action='store_true', help='space_change_sensitive flag')
parser.add_argument('--float_relative_tolerance', type=str, help='float_relative_tolerance flag')
parser.add_argument('--float_absolute_tolerance', type=str, help='float_absolute_tolerance flag')
parser.add_argument('--float_tolerance', type=str, help='float_tolerance flag')
args = parser.parse_args()

main(args)
