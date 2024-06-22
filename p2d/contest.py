import xml.etree.ElementTree
import sys

from argparse import ArgumentParser, ArgumentError
from pathlib import Path

import betterlogging as logging  # type: ignore

from . import __version__


def problem_index_and_name(problem):
    return problem.attrib['index'], problem.attrib['url'].split('/')[-1]


def main():
    parser = ArgumentParser(description='Generate p2d command line arguments from contest.xml')
    parser.add_argument('contest_xml', type=str, help='path of the contest.xml file')
    parser.add_argument('-v', '--version', action='version', version=__version__)
    parser.add_argument('-l', '--log-level', default='info',
                        help='set log level (debug, info, warning, error, critical)')
    args = parser.parse_args()

    logging.basic_colorized_config(level=args.log_level.upper())
    logger = logging.getLogger(__name__)

    contest_xml = Path(args.contest_xml)
    try:
        tree = xml.etree.ElementTree.parse(contest_xml)
        root = tree.getroot()
        problems = root.find('problems')
        logger.info(f'Found {len(problems)} problems in {contest_xml}')
        print('#!/bin/bash')
        print('POLYGON_PACKAGE_DIR=polygon      # change this to the polygon package directory')
        print('DOMJUDGE_PACKAGE_DIR=domjudge    # change this to the domjudge package directory')
        print()
        for problem in problems:
            index, name = problem_index_and_name(problem)
            logger.info(f'Problem {index}: {name}')
            print(f'''# Problem {index}: {name} (change the color if needed)
p2d --yes --code {index} --color "#FF0000" \\
    --output "$DOMJUDGE_PACKAGE_DIR/{name}.zip" --auto \\
    "$POLYGON_PACKAGE_DIR/{name}-*\\$linux.zip"
''')
    except ArgumentError as e:
        logger.error(e)
        sys.exit(2)
    except FileNotFoundError as e:
        logger.error(e)
        sys.exit(1)
    except Exception as e:
        logger.error(e)
        sys.exit(1)


if __name__ == '__main__':
    main()
