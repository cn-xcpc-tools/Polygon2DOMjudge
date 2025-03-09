import re
from pathlib import Path
from typing import Annotated, Optional, cast

import betterlogging as logging  # type: ignore
import typer

from . import __version__
from .p2d import DEFAULT_COLOR, convert
from .typing import Config
from .utils import load_config

app = typer.Typer(pretty_exceptions_show_locals=False)


def version_callback(value: Optional[bool]) -> None:
    if value:
        typer.echo(f"Polygon Package to Domjudge Package v{__version__}")
        raise typer.Exit()


def validate_external_id(value: Optional[str]) -> Optional[str]:
    if value is None or re.match(r"^[a-zA-Z0-9-_]+$", value):
        return value
    raise typer.BadParameter("external-id must contain only letters, numbers, hyphens and underscores")


@app.command(
    no_args_is_help=True,
    help="Process Polygon Package to Domjudge Package.",
    name="problem",
)
def convert_problem(
    package: Annotated[Path, typer.Argument(help="path of the polygon package directory or zip file")],
    short_name: Annotated[
        str,
        typer.Option("--code", "--short-name", help="problem short name in domjudge", prompt=True),
    ],
    color: Annotated[str, typer.Option(help="problem color in domjudge (in #RRGGBB format)")] = DEFAULT_COLOR,
    log_level: Annotated[
        str,
        typer.Option(
            "-l",
            "--log-level",
            help="set log level (debug, info, warning, error, critical)",
        ),
    ] = "info",
    version: Annotated[
        Optional[bool],
        typer.Option(
            "-v",
            "--version",
            help="show version information",
            callback=version_callback,
            is_eager=True,
        ),
    ] = None,
    skip_confirmation: Annotated[bool, typer.Option("-y", "--yes", help="skip confirmation")] = False,
    output: Annotated[
        Optional[Path],
        typer.Option("-o", "--output", help="path of the output package"),
    ] = None,
    auto_detect_std_checker: Annotated[
        bool,
        typer.Option(
            "--auto",
            help="use the default output validator if the checker is defined in config and can be replaced by the default one.",
        ),
    ] = False,
    force_default_validator: Annotated[
        bool, typer.Option("--default", help="force use the default output validator.")
    ] = False,
    validator_flags: Annotated[
        Optional[str],
        typer.Option(help='add some flags to the output validator, only works when "--default" is set.'),
    ] = None,
    memory_limit: Annotated[
        Optional[int],
        typer.Option(
            help="override the memory limit for DOMjudge package (in MB), default is using the memory limit defined in polygon package, -1 means use DOMjudge default"
        ),
    ] = None,
    output_limit: Annotated[
        int,
        typer.Option(
            help="override the output limit for DOMjudge package (in MB), default is using the default output limit in DOMjudge setting, -1 means use DOMjudge default"
        ),
    ] = -1,
    hide_sample: Annotated[
        bool,
        typer.Option(
            help="hide the sample input and output from the problem statement, no sample data will be available for the contestants (force True if this is an interactive problem)."
        ),
    ] = False,
    external_id: Annotated[
        Optional[str],
        typer.Option(
            help="problem external id in domjudge, default is problem id in polygon",
            callback=validate_external_id,
        ),
    ] = None,
    with_statement: Annotated[
        bool,
        typer.Option(
            "--with-statement/--without-statement",
            help="include pdf statement in the package",
        ),
    ] = False,
    with_attachments: Annotated[
        bool,
        typer.Option(
            "--with-attachments/--without-attachments",
            help="include attachments in the package",
        ),
    ] = False,
    testset_name: Annotated[
        Optional[str],
        typer.Option(
            "--testset",
            help="specify the testset to convert, must specify the testset name if the problem has multiple testsets.",
        ),
    ] = None,
    config_file: Annotated[
        Path,
        typer.Option(
            "--config",
            help='path of the config file to override the default config, default is using "config.toml" in current directory',
        ),
    ] = Path("config.toml"),
) -> None:
    logging.basic_colorized_config(level=log_level.upper())
    logger = logging.getLogger(__name__)

    if config_file.is_file():
        logger.info("Using config file: %s", str(config_file))
        config = cast(Config, load_config(config_file))
    else:
        config = None

    if force_default_validator and auto_detect_std_checker:
        raise typer.BadParameter('Cannot use "--default" and "--auto" at the same time.')

    if skip_confirmation:

        def confirm_callback():
            return True
    else:

        def confirm_callback():
            return typer.confirm("Are you sure to convert the package?", abort=True, default=True)

    try:
        convert(
            package=package,
            short_name=short_name,
            color=color,
            confirm=confirm_callback,
            output=output,
            auto_detect_std_checker=auto_detect_std_checker,
            force_default_validator=force_default_validator,
            validator_flags=validator_flags,
            memory_limit=memory_limit,
            output_limit=output_limit,
            hide_sample=hide_sample,
            external_id=external_id,
            with_statement=with_statement,
            with_attachments=with_attachments,
            testset_name=testset_name,
            config=config,
        )
    except Exception as e:
        logger.error(e)
        raise


def main():  # pragma: no cover
    app()
