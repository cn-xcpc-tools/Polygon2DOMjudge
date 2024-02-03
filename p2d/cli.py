import argparse
import errno
import os
import sys
import tempfile
import zipfile

import betterlogging as logging
from pathlib import Path

from . import __version__
from .p2d import Polygon2DOMjudge, DEFAULT_CODE, DEFAULT_COLOR


def main(args=None, raise_exception=False) -> int:

    parser = argparse.ArgumentParser(description='Process Polygon Package to Domjudge Package.')
    parser.add_argument('package', type=Path, help='path of the polygon package directory')
    parser.add_argument('--code', type=str, default=DEFAULT_CODE, help='problem short name in domjudge')
    parser.add_argument('--color', type=str, default=DEFAULT_COLOR, help='problem color in domjudge (in RRGGBB format)')
    parser.add_argument('-l', '--log-level', default='info',
                        help='set log level (debug, info, warning, error, critical)')
    parser.add_argument('-v', '--version', action='version', version=__version__)
    parser.add_argument('-y', '--yes', action='store_true', help='skip confirmation')
    parser.add_argument('-o', '--output', type=Path, help='path of the output package')
    parser.add_argument('--default', action='store_true', help='force use the default output validator.')
    parser.add_argument('--validator-flags', nargs='*', help='add some flags to the output validator, only works when "--default" is set.')
    parser.add_argument('--auto', action='store_true', help='use the default output validator if the checker is defined in config and can be replaced by the default one.')
    parser.add_argument('--memory-limit', type=int,
                        help='override the memory limit for DOMjudge package (in MB), default is using the memory limit defined in polygon package, -1 means use DOMjudge default')  # default use polygon default
    parser.add_argument('--output-limit', type=int, default=-1,
                        help='override the output limit for DOMjudge package (in MB), default is using the default output limit in DOMjudge setting, -1 means use DOMjudge default')
    parser.add_argument('--replace-sample', action='store_true',
                        help='replace the sample input and output with the one shipped with problem statement (e.g. prevent the sample output is different from the main and correct solution).')
    args = parser.parse_args(args)

    logging.basic_colorized_config(level=args.log_level.upper())
    logger = logging.getLogger(__name__)

    def print_info(package_dir, temp_dir, output_file, skip_confirmation=False):
        logger.info('This is Polygon2DOMjudge by cubercsl.')
        logger.info('Process Polygon Package to Domjudge Package.')
        logger.info("Version: {}".format(__version__))

        if sys.platform.startswith('win'):
            logger.warning('It is not recommended running on windows.')

        logger.info(f'Package directory: {package_dir}')
        logger.info(f'Temp directory: {temp_dir}')
        logger.info(f'Output file: {output_file}.zip')
        if not skip_confirmation:
            input("Press enter to continue...")

    with tempfile.TemporaryDirectory(prefix='p2d-polygon-') as polygon_temp_dir, \
            tempfile.TemporaryDirectory(prefix='p2d-domjudge-') as domjudge_temp_dir:

        try:
            package_dir = Path(args.package).resolve()
            if package_dir.is_file():
                with zipfile.ZipFile(args.package, 'r') as zip_ref:
                    logger.info(f'Extracting {package_dir.name} to {polygon_temp_dir}')
                    package_dir = Path(polygon_temp_dir)
                    zip_ref.extractall(package_dir)
            elif package_dir.is_dir():
                logger.info(f'Using {package_dir}')
            else:
                raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), package_dir.name)

            short_name: str = args.code
            color: str = args.color
            replace_sample: bool = args.replace_sample
            output_file = Path.cwd() / short_name

            if args.output:
                if Path(args.output).is_dir():
                    output_file = Path(args.output).resolve() / short_name
                elif args.output.name.endswith('.zip'):
                    output_file = Path(args.output.name[:-4]).resolve()
                else:
                    output_file = Path(args.output).resolve()

            if Path(output_file.name + '.zip').resolve().exists():
                raise FileExistsError(errno.EEXIST, os.strerror(errno.EEXIST), f'{output_file.name}.zip')

            validator_flags = ()

            if args.auto and args.default:
                raise ValueError('Can not use --auto and --default at the same time.')

            if args.default:
                validator_flags = ('__default') + tuple(args.validator_flags or ())
            elif args.validator_flags:
                logger.warning('You are not using default validation, validator flags will be ignored.')

            if args.auto:
                validator_flags = ('__auto')

            print_info(package_dir, domjudge_temp_dir, output_file, args.yes)
            problem = Polygon2DOMjudge(package_dir, domjudge_temp_dir, output_file,
                                       short_name, color, validator_flags, replace_sample, logger)
            # memory_limit and output_limit can be override by command line
            if args.memory_limit:
                problem.memorylimit = args.memory_limit
            if args.output_limit:
                problem.outputlimit = args.output_limit
            problem.process()
        except Exception as e:
            logger.exception(e)
            if raise_exception:
                raise e
            return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
