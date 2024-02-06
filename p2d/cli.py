import argparse
import errno
import os
import sys
import tempfile
import zipfile

import betterlogging as logging  # type: ignore
from pathlib import Path

from . import __version__
from .p2d import Polygon2DOMjudge, DEFAULT_CODE, DEFAULT_COLOR, DEFAULT_CONFIG_FILE
from .utils import load_config, update_dict


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
    parser.add_argument('--hide-sample', action='store_true',
                        help='hide the sample input and output from the problem statement, no sample data will be available for the contestants (force True if this is an interactive problem).')
    parser.add_argument('--config', type=Path, default='config.toml',
                        help='path of the config file to override the default config, default is using "config.toml" in current directory')
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
            hide_sample: bool = args.hide_sample
            auto_detect_std_checker: bool = args.auto
            force_default_validator: bool = args.default
            validator_flags = args.validator_flags if args.validator_flags else []
            output_file = Path.cwd() / short_name
            config = load_config(DEFAULT_CONFIG_FILE)
            config_file = Path(args.config)
            if config_file.is_file():
                logger.info(f'Using config file: {config_file}')
                config_override = load_config(config_file)
            else:
                config_override = {}

            update_dict(config, config_override, add_keys=False)

            if args.output:
                if Path(args.output).is_dir():
                    output_file = Path(args.output).resolve() / short_name
                elif args.output.name.endswith('.zip'):
                    output_file = Path(args.output.name[:-4]).resolve()
                else:
                    output_file = Path(args.output).resolve()

            if Path(output_file.name + '.zip').resolve().exists():
                raise FileExistsError(errno.EEXIST, os.strerror(errno.EEXIST), f'{output_file.name}.zip')

            if args.auto and args.default:
                raise ValueError('Can not use --auto and --default at the same time.')

            if not args.default and args.validator_flags:
                logger.warning('You are not using default validation, validator flags will be ignored.')

            print_info(package_dir, domjudge_temp_dir, output_file, args.yes)
            p = Polygon2DOMjudge(package_dir, domjudge_temp_dir, output_file, short_name, color,
                                 auto_detect_std_checker=auto_detect_std_checker,
                                 force_default_validator=force_default_validator,
                                 validator_flags=validator_flags,
                                 replace_sample=replace_sample,
                                 hide_sample=hide_sample,
                                 config=config)
            # memory_limit and output_limit can be override by command line
            if args.memory_limit:
                p.override_memory_limit(args.memory_limit)
            if args.output_limit:
                p.override_output_limit(args.output_limit)
            p.process()
        except Exception as e:
            logger.exception(e)
            if raise_exception:
                raise e
            return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
