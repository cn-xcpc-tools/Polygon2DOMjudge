import argparse
import json
import logging
import hashlib
import os
import tempfile
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
        logger.info(f'Package directory: {package_dir}')
        logger.info(f'Temp directory: {output_dir}')
        logger.info(f'Output file: {output_file}.zip')
        input("Press enter to continue...")
        logger.info(END_OF_SUBPROCESS)

    def parse_problem():
        logger.info('Parse \'problem.xml\':')
        xml_file = f'{package_dir}/problem.xml'
        root = xml.etree.ElementTree.parse(xml_file)
        name = root.find('names').find('name').attrib['value']
        timelimit = int(root.find('judging').find('testset').find('time-limit').text) / 1000.0
        memlimit = int(root.find('judging').find('testset').find('memory-limit').text) // 1024
        checker = root.find('assets').find('checker')
        interactor = root.find('assets').find('interactor')
        logger.info(f'Problem Name: {name}')
        logger.info(f'Time Limit: {timelimit}')
        logger.info(END_OF_SUBPROCESS)
        return name, timelimit, memlimit, checker, interactor

    def write_ini(probid, timelimit, color):
        logger.info('Add \'domjudge-problem.ini\':')
        ini_file = f'{output_dir}/domjudge-problem.ini'
        ini_content = [
            f'probid = {probid}',
            f'timelimit = {timelimit}',
            f'color = {color}'
        ]
        [*map(logger.info, ini_content)]
        with open(ini_file, 'w', encoding='utf-8') as f:
            f.writelines(map(lambda s: s + '\n', ini_content))
        logger.info(END_OF_SUBPROCESS)

    def write_yaml(name, memlimit):
        logger.info('Add \'problem.yaml\':')
        yaml_file = f'{output_dir}/problem.yaml'
        name = name.replace('"', r'\"')
        yaml_content = f'name: "{name}"\nlimits:\n  memory: {memlimit}\n'
        logger.info(yaml_content)
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

        yaml_file = f'{output_dir}/problem.yaml'
        output_validators_dir = f'{output_dir}/output_validators'
        checker_dir = f'{output_validators_dir}/checker'
        interactor_dir = f'{output_validators_dir}/interactor'
        if args.default:
            with open(yaml_file, 'w', encoding='utf-8') as f:
                f.write(yaml_content)
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
                    f.write(yaml_content)
                    f.write('validation: custom interactive\n')
                ensure_dir(interactor_dir)
                copyfile(testlib, f'{interactor_dir}/testlib.h', follow_symlinks=False)
                interactor_path = interactor.find('source').attrib['path']
                interactor_file = f'{package_dir}/{interactor_path}'
                copyfile(interactor_file, f'{interactor_dir}/interactor.cpp')
            elif checker is not None:
                logger.info('Use custom checker.')
                with open(yaml_file, 'w', encoding='utf-8') as f:
                    f.write(yaml_content)
                    f.write('validation: custom\n')
                ensure_dir(checker_dir)
                copyfile(testlib, f'{checker_dir}/testlib.h', follow_symlinks=False)
                checker_path = checker.find('source').attrib['path']
                checker_file = f'{package_dir}/{checker_path}'
                copyfile(checker_file, f'{checker_dir}/checker.cpp')
            else:
                raise Exception('No checker found.')
        logger.info(END_OF_SUBPROCESS)

    def add_test():
        logger.info('Add tests:')
        ensure_dir(f'{output_dir}/data')
        ensure_dir(f'{output_dir}/data/sample')
        ensure_dir(f'{output_dir}/data/secret')

        for test in filter(lambda x: not x.endswith(extention_for_output), os.listdir(f'{package_dir}/tests')):
            input_src = f'{package_dir}/tests/{test}'
            output_src = f'{package_dir}/tests/{test}{extention_for_output}'
            if test in samples:
                input_dst = f'{output_dir}/data/sample/{test}.in'
                output_dst = f'{output_dir}/data/sample/{test}.ans'
                logger.info(f'* sample: {test}.(in/ans)')
            else:
                input_dst = f'{output_dir}/data/secret/{test}.in'
                output_dst = f'{output_dir}/data/secret/{test}.ans'
                logger.info(f'* secret: {test}.(in/ans)')
            copyfile(input_src, input_dst)
            copyfile(output_src, output_dst)
        logger.info(END_OF_SUBPROCESS)

    def add_jury_solution():
        logger.info('Add jury solutions:')
        ensure_dir(f'{output_dir}/submissions')
        ensure_dir(f'{output_dir}/submissions/accepted')
        ensure_dir(f'{output_dir}/submissions/wrong_answer')
        ensure_dir(f'{output_dir}/submissions/time_limit_exceeded')
        ensure_dir(f'{output_dir}/submissions/run_time_error')

        def get_solution(desc):
            result = {}
            desc_file = f'{package_dir}/solutions/{desc}'
            with open(desc_file, 'r', encoding='utf-8') as f:
                for _ in f.readlines():
                    key, value = _.strip().split(': ', maxsplit=2)
                    if key == 'File name':
                        result[key] = value
                    elif key == 'Tag':
                        try:
                            if value not in config['tag'].keys():
                                raise Exception(f'Unknown tag: {value}')
                            result[key] = config['tag'][value]
                        except KeyError:
                            logger.warning(f'Treat unknown tag \'{value}\' as \'accepted\'.')
                            result[key] = 'accepted'
            if not ('File name' in result.keys() or 'Tag' in result.keys()):
                raise Exception(f'The description file {desc} has error.')
            return result['File name'], result['Tag']

        for desc in filter(lambda x: x.endswith(extention_for_desc), os.listdir(f'{package_dir}/solutions')):
            solution, result = get_solution(desc)
            src = f'{package_dir}/solutions/{solution}'
            dst = f'{output_dir}/submissions/{result}/{solution}'
            print(src, dst)
            copyfile(src, dst)
            logger.info(f'- {solution} (Expected Result: {result})')
        logger.info(END_OF_SUBPROCESS)

    testlib = (os.getenv('TESTLIB_PATH', '.')).rstrip('/') + '/testlib.h'
    extention_for_output = os.getenv('EXTENTION_FOR_OUTPUT', '.a')
    extention_for_desc = os.getenv('EXTENTION_FOR_DESC', '.desc')
    probid = 'PROB1'
    color = '#000000'
    samples = ['01']
    package_dir = args.package.rstrip('/')
    output_file = args.package.rstrip('/')
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

    with tempfile.TemporaryDirectory() as output_dir:
        start(package_dir, output_dir, output_file)
        try:
            name, timelimit, memlimit, checker, interactor = parse_problem()
            write_ini(probid, timelimit, color)
            write_yaml(name, memlimit)
            add_test()
            add_jury_solution()
            make_archive(output_file, 'zip', output_dir)
            ensure_no_dir(output_dir)
            logger.info('Make package {}.zip success.'.format(output_file.split('/')[-1]))
        except Exception as e:
            logger.error(e)

log_path = os.getenv('LOG_PATH', '.')
ensure_dir(log_path)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler('{}/{}.log'.format(log_path, strftime('%Y-%m-%d %H:%M:%S', localtime(time()))))
console = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(console)
logger.addHandler(handler)


config_file = (os.getenv('CONFIG_PATH', '.')).rstrip('/') + '/config.json'
try:
    with open(config_file, 'r', encoding='utf-8') as f:
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
