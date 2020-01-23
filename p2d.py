#!/usr/bin/python3
import argparse
import hashlib
import math
import os
import sys
import xml.etree.ElementTree
from shutil import copyfile, rmtree, make_archive

INI_CONTENT = '''probid = {}
name = {}
timelimit = {}
color = {}
'''

STD_CHECKERS_MD5 = {}
with open('./checkers/md5sum', 'r', encoding='utf-8') as f:
    for _ in f.readlines():
        md5, name = _.strip().split(maxsplit=2)
        STD_CHECKERS_MD5[md5] = name

TAG_REMAP = {
    'MAIN': 'accepted',
    'ACCEPTED': 'accepted',
    'WRONG_ANSWER': 'wrong_answer',
    'PRESENTATION_ERROR': 'wrong_answer',
    'TIME_LIMIT_EXCEEDED': 'time_limit_exceed',
    'TIME_LIMIT_EXCEEDED_OR_ACCEPTED': 'time_limit_exceed',
    # DOMjudge return RE when MLE.
    'TIME_LIMIT_EXCEEDED_OR_MEMORY_LIMIT_EXCEEDED': 'run_time_error',
    'MEMORY_LIMIT_EXCEEDED': 'rum_time_error',
    # We think REJUECTED or FAILED means RE.
    'REJECTED': 'run_time_error',
    'FAILED': 'run_time_error'
}
END_OF_SUBPROCESS = '=' * 50


def main(args):
    def ensure_dir(s):
        if not os.path.exists(s):
            os.makedirs(s)

    def ensure_no_dir(s):
        if os.path.exists(s):
            rmtree(s)

    def start():
        print('This is p2d.py by cubercsl.')
        print('Process Polygon Package to Domjudge Package.')
        print(END_OF_SUBPROCESS)

    def parse_problem():
        xml_file = '{}/problem.xml'.format(package_dir)
        root = xml.etree.ElementTree.parse(xml_file)
        name = root.find('names').find('name').attrib['value']
        timelimit = float(math.ceil(float(root.find('judging').find('testset').find('time-limit').text) / 1000.0))
        checker = root.find('assets').find('checker')
        interactor = root.find('assets').find('interactor')
        print('Problem Name: {}'.format(name))
        print('Time Limit: {}'.format(timelimit))
        print(END_OF_SUBPROCESS)
        return name, timelimit, checker, interactor

    def write_ini(probid, name, timelimit, color):
        print('Add \'domjudge-problem.ini\':')
        ini_file = '{}/domjudge-problem.ini'.format(output_dir)
        ini_content = INI_CONTENT.format(probid, name, timelimit, color)
        print(ini_content, end='')
        with open(ini_file, 'w', encoding='utf-8') as f:
            f.write(ini_content)
        print(END_OF_SUBPROCESS)

    def add_output_validator():
        print('Add output validator:')

        def get_checker_md5(checker):
            if checker is None:
                return None
            checker_source = checker.find('source')
            checker_file = '{}/{}'.format(package_dir, checker_source.attrib['path'])
            with open(checker_file, 'r', encoding='utf-8') as f:
                file_md5 = hashlib.md5(f.read().replace('\r\n', '\n').encode('utf-8'))
            return file_md5.hexdigest().lower()

        checker_md5 = get_checker_md5(checker)
        print('Checker md5: {}'.format(checker_md5))

        if checker_md5 in STD_CHECKERS_MD5.keys():
            args.default = True
            checker_name = STD_CHECKERS_MD5[checker_md5]
            print('Use std checker: std::{}.'.format(checker_name))
            if checker_name == 'rcmp4.cpp':
                args.float_tolerance = '1e-4'
            elif checker_name == 'rcmp6.cpp':
                args.float_tolerance = '1e-6'
            elif checker_name == 'rcmp9.cpp':
                args.float_tolerance = '1e-9'
            elif checker_name == 'fcmp.cpp':
                args.case_sensitive = True
                args.space_change_sensitive = True

        yaml_file = '{}/problem.yaml'.format(output_dir)
        output_validators_dir = '{}/output_validators'.format(output_dir)
        checker_dir = '{}/checker'.format(output_validators_dir)
        interactor_dir = '{}/interactor'.format(output_validators_dir)
        if args.default:
            with open(yaml_file, 'w+', encoding='utf-8') as f:
                f.write('validation: default\n')
                validator_flags = []
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
                    f.write('validator_flags: ' +
                            ' '.join(validator_flags) + '\n')
        else:
            ensure_dir(output_validators_dir)
            if interactor is not None:
                print('Use custom interactor.')
                with open(yaml_file, 'w+', encoding='utf-8') as f:
                    f.write('validation: custom interactive\n')
                ensure_dir(interactor_dir)
                copyfile('./testlib.h', '{}/testlib.h'.format(interactor_dir))
                interactor_file = '{}/{}'.format(package_dir,
                                                 interactor.find('source').attrib['path'])
                copyfile(interactor_file,
                         '{}/interactor.cpp'.format(interactor_dir))
            elif checker is not None:
                print('Use custom checker.')
                with open(yaml_file, 'w+', encoding='utf-8') as f:
                    f.write('validation: custom\n')
                ensure_dir(interactor_dir)
                copyfile('./testlib.h', '{}/testlib.h'.format(interactor_dir))
                checker_file = '{}/{}'.format(package_dir,
                                              checker.find('source').attrib['path'])
                copyfile(checker_file,
                         '{}/checker.cpp'.format(checker_dir))
        print(END_OF_SUBPROCESS)

    def add_test():
        print('Add tests:')
        ensure_dir('{}/data'.format(output_dir))
        ensure_dir('{}/data/sample'.format(output_dir))
        ensure_dir('{}/data/secret'.format(output_dir))

        for test in filter(lambda x: not x.endswith(extention_for_output),
                           os.listdir('{}/tests'.format(package_dir))):
            input_src = '{}/tests/{}'.format(package_dir, test)
            output_src = '{}/tests/{}{}'.format(package_dir,
                                                test, extention_for_output)
            if test in samples:
                input_dst = '{}/data/sample/{}.in'.format(output_dir, test)
                output_dst = '{}/data/sample/{}.ans'.format(output_dir, test)
                print('- sample: {}.'.format(test))
            else:
                input_dst = '{}/data/secret/{}.in'.format(output_dir, test)
                output_dst = '{}/data/secret/{}.ans'.format(output_dir, test)
                print('- secret: {}.'.format(test))
            copyfile(input_src, input_dst)
            copyfile(output_src, output_dst)
        print(END_OF_SUBPROCESS)

    def add_jury_solution():
        print('Add jury solutions:')
        ensure_dir('{}/submissions'.format(output_dir))
        ensure_dir('{}/submissions/accepted'.format(output_dir))
        ensure_dir('{}/submissions/wrong_answer'.format(output_dir))
        ensure_dir('{}/submissions/time_limit_exceeded'.format(output_dir))
        ensure_dir('{}/submissions/run_time_error'.format(output_dir))

        def get_solution(desc):
            result = {}
            desc_file = '{}/solutions/{}'.format(package_dir, desc)
            with open(desc_file, 'r') as f:
                for _ in f.readlines():
                    key, value = _.strip().split(': ', maxsplit=2)
                    if key == 'File name':
                        result[key] = value
                    elif key == 'Tag':
                        if value not in TAG_REMAP.keys():
                            raise Exception('Unknown tag: ' + value)
                        result[key] = TAG_REMAP[value]
            if not ('File name' in result.keys() or 'Tag' in result.keys()):
                raise Exception('The description file %s has error.' % desc)
            return result['File name'], result['Tag']

        for desc in filter(lambda x: x.endswith(extention_for_desc),
                           os.listdir('{}/solutions'.format(package_dir))):
            solution, result = get_solution(desc)
            src = '{}/solutions/{}'.format(package_dir, solution)
            dst = '{}/submissions/{}/{}'.format(
                output_dir, result, solution)
            copyfile(src, dst)
            print('- {} (Expected Result: {})'.format(
                solution, result))
        print(END_OF_SUBPROCESS)

    output_dir = (os.getenv('OUTPUT_DIR') or './tmp').strip('/')
    extention_for_output = os.getenv('EXTENTION_FOR_OUTPUT') or '.a'
    extention_for_desc = os.getenv('EXTENTION_FOR_DESC') or '.desc'
    probid = 'PROB1'
    color = '#000000'
    samples = ['01']
    package_dir = args.package.strip('/')
    output_file = args.package
    if args.code: probid = args.code
    if args.color: color = args.color
    if args.sample: samples = [args.sample]
    if args.num_samples:
        assert len(samples) == 1
        first = int(samples[0])
        num_samples = int(args.num_samples)
        assert (num_samples < 100)
        samples = ['{0:02d}'.format(
            i) for i in range(first, first + num_samples)]
    if args.output: output_file = args.output

    ensure_no_dir(output_dir)
    ensure_dir(output_dir)

    try:
        start()
        name, timelimit, checker, interactor = parse_problem()
        write_ini(probid, name, timelimit, color)
        add_output_validator()
        add_test()
        add_jury_solution()
        make_archive(output_file, 'zip', output_dir)
        ensure_no_dir(output_dir)
        print('Make package {}.zip success.'.format(output_file))
    except Exception as e:
        print(e, file=sys.stderr)


parser = argparse.ArgumentParser(description='Process Polygon Package to Domjudge Package.')
parser.add_argument('package', type=str, help='path of the polygon package')
parser.add_argument('--code', type=str, help='problem code for domjudge')
parser.add_argument('--sample', type=str, help='Specify the filename for sample test. Defaults to \'01\'')
parser.add_argument('--num-samples', type=str, help='Specify the number of sample test cases. Defaults to \'1\'')
parser.add_argument('--color', type=str, help='problem color for domjudge (in RRGGBB format)')
parser.add_argument('-o', '--output', type=str, help='Output Package directory')
parser.add_argument('--default', action='store_true', help='Use default validation')
parser.add_argument('--case_sensitive', action='store_true', help='case_sensitive flag')
parser.add_argument('--space_change_sensitive', action='store_true', help='space_change_sensitive flag')
parser.add_argument('--float_relative_tolerance', type=str, help='float_relative_tolerance flag')
parser.add_argument('--float_absolute_tolerance', type=str, help='float_absolute_tolerance flag')
parser.add_argument('--float_tolerance', type=str, help='float_tolerance flag')
args = parser.parse_args()
main(args)
