import sys
from argparse import ArgumentParser, ArgumentError
from pathlib import Path
from typing import cast, List, Optional

import betterlogging as logging  # type: ignore

from . import __version__
from .p2d import convert, DEFAULT_CODE, DEFAULT_COLOR
from .utils import load_config
from .typing import Config


def main(argv: Optional[List[str]] = None) -> int:

    parser = ArgumentParser(description='Process Polygon Package to Domjudge Package.')
    parser.add_argument('package', type=Path, help='path of the polygon package directory')
    parser.add_argument('--code', type=str, default=DEFAULT_CODE, help='problem short name in domjudge')
    parser.add_argument('--color', type=str, default=DEFAULT_COLOR,
                        help='problem color in domjudge (in #RRGGBB format)')
    parser.add_argument('-l', '--log-level', default='info',
                        help='set log level (debug, info, warning, error, critical)')
    parser.add_argument('-v', '--version', action='version', version=__version__)
    parser.add_argument('-y', '--yes', action='store_true', help='skip confirmation')
    parser.add_argument('-o', '--output', type=Path, help='path of the output package')
    parser.add_argument('--default', action='store_true', help='force use the default output validator.')
    parser.add_argument('--validator-flags', nargs='*',
                        help='add some flags to the output validator, only works when "--default" is set.')
    parser.add_argument('--auto', action='store_true',
                        help='use the default output validator if the checker is defined in config and can be replaced by the default one.')
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
    args = parser.parse_args(argv)

    logging.basic_colorized_config(level=args.log_level.upper())
    logger = logging.getLogger(__name__)

    try:
        config_file = Path(args.config)
        if config_file.is_file():
            logger.info(f'Using config file: {config_file}')
            config = cast(Config, load_config(config_file))
        else:
            config = None

        if args.auto and args.default:
            raise ArgumentError(None, 'You cannot use both "--auto" and "--default" at the same time.')

        if not args.default and args.validator_flags:
            logger.warning('You are not using default validation, validator flags will be ignored.')

        _kwargs = {
            'short_name': args.code,
            'color': args.color,
            'replace_sample': args.replace_sample,
            'hide_sample': args.hide_sample,
            'auto_detect_std_checker': args.auto,
            'force_default_validator': args.default,
            'validator_flags': args.validator_flags,
            'memory_limit': args.memory_limit,
            'output_limit': args.output_limit,
            'skip_confirmation': args.yes,
            'config': config,
        }

        convert(
            args.package,
            args.output,
            **_kwargs,
        )
    except ArgumentError as e:
        logger.error(e)
        sys.exit(2)
    except (FileNotFoundError, FileExistsError) as e:
        logger.error(e)
        sys.exit(1)
    except Exception as e:
        logger.exception(e)
        sys.exit(1)
    return 0


if __name__ == '__main__':
    sys.exit(main())
