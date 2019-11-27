#!/usr/bin/python3
import argparse,os,math,sys
from shutil import copyfile, make_archive, rmtree
import xml.etree.ElementTree

def ensure_dir(s):
    if not os.path.exists(s):
        os.makedirs(s)

def ensure_no_dir(s):
	if os.path.exists(s):
		rmtree(s)

OUTPUT_DIR = './tmp'
EXTENSION_FOR_OUTPUT = '.a'
EXTENSION_FOR_DESC = '.desc'
EXTENSION_FOR_EXE = '.exe'
PROBCODE = "PROB1"
PROBCOLOR = "#000000"
sample_tests = ['01']

parser = argparse.ArgumentParser(description='Process Polygon Package to Domjudge Package.')
parser.add_argument('package', type=str, help='path of the polygon package')
parser.add_argument('--code',  type=str, help='problem code for domjudge')
parser.add_argument('--sample',type=str, help='Specify the filename for sample test. Defaults to \'01\'')
parser.add_argument('--num-samples', type=str, help='Specify the number of sample test cases. Defaults to \'1\'')
parser.add_argument('--color', type=str, help='problem color for domjudge (in RRGGBB format)')
parser.add_argument('-o','--output', type=str, help='Output Package directory')
parser.add_argument('--ext', type=str, help='Set extension for the OUTPUT files in testset')
parser.add_argument('--default', action='store_true', help='Use default validation')
parser.add_argument('--case_sensitive', action='store_true', help='case_sensitive flag')
parser.add_argument('--space_change_sensitive', action='store_true', help='space_change_sensitive flag')
parser.add_argument('--float_relative_tolerance', type=str, help='float_relative_tolerance flag')
parser.add_argument('--float_absolute_tolerance', type=str, help='float_absolute_tolerance flag')
parser.add_argument('--float_tolerance', type=str, help='float_tolerance flag')
args = parser.parse_args()

PACKAGE_DIR = args.package

if args.code:
    PROBCODE = args.code

if args.color:
	PROBCOLOR = '#' + args.color

if args.sample:
	sample_tests = [args.sample]

if args.num_samples:
    assert len(sample_tests) == 1
    first = int(sample_tests[0])
    num_samples = int(args.num_samples)
    assert(num_samples < 100)
    sample_tests = ['{0:02d}'.format(i) for i in range(first, first + num_samples)]

if args.output:
	OUTPUT_DIR = args.output

if args.ext:
	EXTENSION_FOR_OUTPUT = args.ext

PACKAGE_DIR = PACKAGE_DIR.strip('/')
OUTPUT_DIR = OUTPUT_DIR.strip('/')

ensure_no_dir(OUTPUT_DIR)
ensure_dir(OUTPUT_DIR)

ensure_dir(OUTPUT_DIR + '/data')
ensure_dir(OUTPUT_DIR + '/data/sample')
ensure_dir(OUTPUT_DIR + '/data/secret')

ensure_dir(OUTPUT_DIR + '/submissions')
ensure_dir(OUTPUT_DIR + '/submissions/accepted')
ensure_dir(OUTPUT_DIR + '/submissions/wrong_answer')
ensure_dir(OUTPUT_DIR + '/submissions/time_limit_exceeded')

root = xml.etree.ElementTree.parse(PACKAGE_DIR + '/problem.xml').getroot()
problem_name = root.find('names').find('name').attrib['value']
timelimit = float(math.ceil(float(root.find('judging').find('testset').find('time-limit').text)/1000.0))

desc = open(OUTPUT_DIR + '/domjudge-problem.ini','w+')
desc.write("probid = " + PROBCODE + "\n")
desc.write("name = " + problem_name.replace("'","`") + "\n")
desc.write("timelimit = " + str(timelimit) + "\n")
desc.write("color = " + PROBCOLOR + "\n")
desc.close()
interactor = root.find('assets').find('interactor')
checker = root.find('assets').find('checker')
if args.default:
    desc = open(OUTPUT_DIR+'/problem.yaml', 'w+')
    desc.write("validation: default\n")
    validator_flags = []
    if args.case_sensitive:
        validator_flags.append("case_sensitive")
    if args.space_change_sensitive:
        validator_flags.append("space_change_sensitive")
    if args.float_relative_tolerance:
        validator_flags.append("float_relative_tolerance")
        validator_flags.append(args.float_relative_tolerance)
    if args.float_absolute_tolerance:
        validator_flags.append("float_absolute_tolerance")
        validator_flags.append(args.float_absolute_tolerance)
    if args.float_tolerance:
        validator_flags.append("float_tolerance")
        validator_flags.append(args.float_tolerance)
    if validator_flags:
        desc.write("validator_flags: " + ' '.join(validator_flags) + "\n")
    desc.close()
else:
    if interactor is not None:
        ensure_dir(OUTPUT_DIR + '/output_validators')
        desc = open(OUTPUT_DIR + '/problem.yaml', 'w+')
        desc.write("validation: custom interactive\n")
        desc.close()
        INTERACTOR_DIR = OUTPUT_DIR + '/output_validators/interactor'
        ensure_dir(INTERACTOR_DIR)
        copyfile("./testlib.h", INTERACTOR_DIR + '/testlib.h')
        interactor_source = interactor.find('source')
        copyfile(PACKAGE_DIR + '/' + interactor_source.attrib['path'], INTERACTOR_DIR + '/interactor.cpp')
    elif checker is not None:
        ensure_dir(OUTPUT_DIR + '/output_validators')
        desc = open(OUTPUT_DIR+'/problem.yaml', 'w+')
        desc.write("validation: custom\n")
        desc.close()
        CHECKER_DIR = OUTPUT_DIR + '/output_validators/checker'
        ensure_dir(CHECKER_DIR)
        copyfile("./testlib.h", CHECKER_DIR + '/testlib.h')
        checker_source = checker.find('source')
        copyfile(PACKAGE_DIR + '/' + checker_source.attrib['path'], CHECKER_DIR + '/checker.cpp')


tests = filter(lambda x:not x.endswith(EXTENSION_FOR_OUTPUT),os.listdir(PACKAGE_DIR + '/tests'))
for test in tests:
	if test in sample_tests:
		copyfile(PACKAGE_DIR + '/tests/' + test,OUTPUT_DIR + '/data/sample/' + test + '.in')
		copyfile(PACKAGE_DIR + '/tests/' + test+EXTENSION_FOR_OUTPUT,OUTPUT_DIR + '/data/sample/' + test + '.ans')
	else:
		copyfile(PACKAGE_DIR + '/tests/' + test,OUTPUT_DIR + '/data/secret/' + test + '.in')
		copyfile(PACKAGE_DIR + '/tests/' + test+EXTENSION_FOR_OUTPUT,OUTPUT_DIR + '/data/secret/' + test + '.ans')

jury_solutions = filter(lambda x : not (x.endswith(EXTENSION_FOR_DESC) or x.endswith(EXTENSION_FOR_EXE)) , os.listdir(PACKAGE_DIR + '/solutions'))
for solution in jury_solutions:
    copyfile(PACKAGE_DIR + '/solutions/' + solution, OUTPUT_DIR + '/submissions/accepted/' + solution)
