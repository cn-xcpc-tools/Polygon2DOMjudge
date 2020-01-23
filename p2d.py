#!/usr/bin/python3
import argparse
import os
import math
from shutil import copyfile, rmtree, make_archive
import xml.etree.ElementTree
import hashlib


def ensure_dir(s):
    if not os.path.exists(s):
        os.makedirs(s)


def ensure_no_dir(s):
    if os.path.exists(s):
        rmtree(s)


OUTPUT_DIR = os.getenv('OUTPUT_DIR') or './tmp'
EXTENSION_FOR_OUTPUT = os.getenv('EXTENSION_FOR_OUTPUT') or '.a'
EXTENSION_FOR_DESC = os.getenv('EXTENSION_FOR_DESC') or '.desc'
EXTENSION_FOR_EXE = os.getenv('EXTENSION_FOR_EXE') or '.exe'

PROBCODE = "PROB1"
PROBCOLOR = "#000000"
SAMPLES = ['01']

parser = argparse.ArgumentParser(
    description='Process Polygon Package to Domjudge Package.')
parser.add_argument('package', type=str, help='path of the polygon package')
parser.add_argument('--code', type=str, help='problem code for domjudge')
parser.add_argument('--sample', type=str,
                    help='Specify the filename for sample test. Defaults to \'01\'')
parser.add_argument('--num-samples', type=str,
                    help='Specify the number of sample test cases. Defaults to \'1\'')
parser.add_argument('--color', type=str,
                    help='problem color for domjudge (in RRGGBB format)')
parser.add_argument('-o', '--output', type=str,
                    help='Output Package directory')
parser.add_argument('--default', action='store_true',
                    help='Use default validation')
parser.add_argument('--case_sensitive', action='store_true',
                    help='case_sensitive flag')
parser.add_argument('--space_change_sensitive',
                    action='store_true', help='space_change_sensitive flag')
parser.add_argument('--float_relative_tolerance', type=str,
                    help='float_relative_tolerance flag')
parser.add_argument('--float_absolute_tolerance', type=str,
                    help='float_absolute_tolerance flag')
parser.add_argument('--float_tolerance', type=str, help='float_tolerance flag')

args = parser.parse_args()

# parse args
PACKAGE_DIR = args.package
OUTPUT_FILE = args.package

if args.code:
    PROBCODE = args.code

if args.color:
    PROBCOLOR = '#' + args.color

if args.sample:
    SAMPLES = [args.sample]

if args.num_samples:
    assert len(SAMPLES) == 1
    first = int(SAMPLES[0])
    num_samples = int(args.num_samples)
    assert (num_samples < 100)
    SAMPLES = ['{0:02d}'.format(i) for i in range(first, first + num_samples)]

if args.output:
    OUTPUT_FILE = args.output

PACKAGE_DIR = PACKAGE_DIR.strip('/')
OUTPUT_DIR = OUTPUT_DIR.strip('/')

ensure_no_dir(OUTPUT_DIR)
ensure_dir(OUTPUT_DIR)

# parse the problem name and timelimit
root = xml.etree.ElementTree.parse(PACKAGE_DIR + '/problem.xml').getroot()
name = root.find('names').find('name').attrib['value']
timelimit = float(math.ceil(float(root.find('judging').find(
    'testset').find('time-limit').text) / 1000.0))

print('Problem Name: ' + name)
print('Time Limit: ' + str(timelimit))

# write 'domjudge-problem.ini'
print('Write \'domjudge-problem.ini\'')
desc = open(OUTPUT_DIR + '/domjudge-problem.ini', 'w+', encoding='utf-8')
desc.write("probid = " + PROBCODE + '\n')
desc.write("name = " + name.replace("'", "`") + '\n')
desc.write("timelimit = " + str(timelimit) + '\n')
desc.write("color = " + PROBCOLOR + '\n')
desc.close()

# search for the checker/interactor
checker = root.find('assets').find('checker')
interactor = root.find('assets').find('interactor')

# check if use std checker
STD_CHECKER_MD5 = {}
with open('./checker/md5sum', 'r', encoding='utf-8') as f:
    for _ in f.readlines():
        md5, name = _.strip().split(maxsplit=2)
        STD_CHECKER_MD5[md5] = name


def get_checker_md5():
    if checker is None:
        return None
    checker_source = checker.find('source')
    checker_file = PACKAGE_DIR + '/' + checker_source.attrib['path']
    with open(checker_file) as f:
        file_md5 = hashlib.md5(f.read().replace(
            '\r\n', '\n').encode('utf-8')).hexdigest().lower()
    return file_md5


checker_md5 = get_checker_md5()
if checker_md5 in STD_CHECKER_MD5.keys():
    args.default = True
    checker_name = STD_CHECKER_MD5[checker_md5]
    print('Use std checker: std::' + checker_name + '.')
    if (checker_name == 'rcmp4.cpp'):
        args.float_tolerance = '1e-4'
    if (checker_name == 'rcmp6.cpp'):
        args.float_tolerance = '1e-6'
    if (checker_name == 'rcmp9.cpp'):
        args.float_tolerance = '1e-9'
    if (checker_name == 'fcmp.cpp'):
        args.case_sensitive = True

# add output validator
CHECKER_DIR = OUTPUT_DIR + '/output_validators/checker'
INTERACTOR_DIR = OUTPUT_DIR + '/output_validators/interactor'

if args.default:
    desc = open(OUTPUT_DIR + '/problem.yaml', 'w+', encoding='utf-8')
    desc.write('validation: default\n')
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
        desc.write('validator_flags: ' + ' '.join(validator_flags) + '\n')
    desc.close()
else:
    ensure_dir(OUTPUT_DIR + '/output_validators')
    if interactor is not None:
        print('Use custom interactor.')
        desc = open(OUTPUT_DIR + '/problem.yaml', 'w+', encoding='utf-8')
        desc.write('validation: custom interactive\n')
        desc.close()
        ensure_dir(INTERACTOR_DIR)
        copyfile('./testlib.h', INTERACTOR_DIR + '/testlib.h')
        interactor_source = interactor.find('source')
        copyfile(PACKAGE_DIR + '/' +
                 interactor_source.attrib['path'], INTERACTOR_DIR + '/interactor.cpp')
    elif checker is not None:
        print('Use custom checker.')
        desc = open(OUTPUT_DIR + '/problem.yaml', 'w+', encoding='utf-8')
        desc.write('validation: custom\n')
        desc.close()
        ensure_dir(CHECKER_DIR)
        copyfile('./testlib.h', CHECKER_DIR + '/testlib.h')
        checker_source = checker.find('source')
        copyfile(PACKAGE_DIR + '/' +
                 checker_source.attrib['path'], CHECKER_DIR + '/checker.cpp')
    else:
        print('No checker find.')
        exit()

# add tests
ensure_dir(OUTPUT_DIR + '/data')
ensure_dir(OUTPUT_DIR + '/data/sample')
ensure_dir(OUTPUT_DIR + '/data/secret')

for test in filter(lambda x: not x.endswith(EXTENSION_FOR_OUTPUT),
                   os.listdir(PACKAGE_DIR + '/tests')):
    if test in SAMPLES:
        copyfile(PACKAGE_DIR + '/tests/' + test,
                 OUTPUT_DIR + '/data/sample/' + test + '.in')
        copyfile(PACKAGE_DIR + '/tests/' + test + EXTENSION_FOR_OUTPUT,
                 OUTPUT_DIR + '/data/sample/' + test + '.ans')
        print('Add a sample test: ' + test + '.')
    else:
        copyfile(PACKAGE_DIR + '/tests/' + test,
                 OUTPUT_DIR + '/data/secret/' + test + '.in')
        copyfile(PACKAGE_DIR + '/tests/' + test + EXTENSION_FOR_OUTPUT,
                 OUTPUT_DIR + '/data/secret/' + test + '.ans')
        print('Add a secret test: ' + test + '.')

# add jury solutions
ensure_dir(OUTPUT_DIR + '/submissions')
ensure_dir(OUTPUT_DIR + '/submissions/accepted')
ensure_dir(OUTPUT_DIR + '/submissions/wrong_answer')
ensure_dir(OUTPUT_DIR + '/submissions/time_limit_exceeded')
ensure_dir(OUTPUT_DIR + '/submissions/run_time_error')

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


def get_solution(desc):
    result = {}
    with open(PACKAGE_DIR + '/solutions/' + desc, 'r') as f:
        for item in f.readlines():
            key, value = item.strip().split(': ', maxsplit=2)
            if (key == 'File name'):
                result[key] = value
            if (key == 'Tag'):
                if not value in TAG_REMAP.keys():
                    raise Exception('Unknown tag: ' + value)
                result[key] = TAG_REMAP[value]
    if not ('File name' in result.keys() or 'Tag' in result.keys()):
        raise Exception('The description file %s has error.' % desc)
    return result['File name'], result['Tag']


for desc in filter(lambda x: x.endswith(EXTENSION_FOR_DESC),
                   os.listdir(PACKAGE_DIR + '/solutions')):
    try:
        solution, result = get_solution(desc)
        copyfile(PACKAGE_DIR + '/solutions/' + solution,
                 OUTPUT_DIR + '/submissions/' + result + '/' + solution)
        print('Add a jury solution: ' + result + '/' + solution + '.')
    except Exception as e:
        print(e)

make_archive(OUTPUT_FILE, 'zip', OUTPUT_DIR)
ensure_no_dir(OUTPUT_DIR)
print('Make package success.')
