import logging
import re
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.logging import RichHandler

from ._version import __version__
from .models import GlobalConfig
from .p2d import DEFAULT_COLOR, convert
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
    global_config_file: Annotated[
        Optional[Path],
        typer.Option(
            "-c",
            "--config",
            help='path of the config file to override the default global config, default is using "config.toml" in current directory if exists.',
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
        ),
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
    keep_sample: Annotated[
        Optional[list[int]],
        typer.Option(
            "--keep",
            "--keep-sample",
            help="keep the specified numbered sample output from the main and correct solution, can be used multiple times, (e.g. --keep 1 --keep 2), default is replacing all sample output with problem statement.",
        ),
    ] = None,
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
) -> None:
    logging.basicConfig(
        level=log_level.upper(),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, console=Console(stderr=True))],
    )
    logger = logging.getLogger(__name__)

    if Path("config.toml").is_file():
        global_config_file = Path("config.toml")

    if global_config_file is not None and global_config_file.is_file():
        logger.info("Using config file: %s", str(global_config_file))
        global_config = load_config(global_config_file)
    else:
        global_config = GlobalConfig()

    if force_default_validator and auto_detect_std_checker:
        raise typer.BadParameter('Cannot use "--default" and "--auto" at the same time.')

    if skip_confirmation:

        def confirm_callback() -> bool:
            return True
    else:

        def confirm_callback() -> bool:
            return typer.confirm("Are you sure to convert the package?", abort=True, default=True, err=True)

    try:
        convert(
            package=package,
            short_name=short_name,
            color=color,
            confirm=confirm_callback,
            output=output,
            global_config=global_config,
            auto_detect_std_checker=auto_detect_std_checker,
            force_default_validator=force_default_validator,
            validator_flags=validator_flags,
            memory_limit=memory_limit,
            output_limit=output_limit,
            hide_sample=hide_sample,
            keep_sample=keep_sample,
            external_id=external_id,
            with_statement=with_statement,
            with_attachments=with_attachments,
            testset_name=testset_name,
        )
    except Exception as e:
        logger.error(e)
        raise
