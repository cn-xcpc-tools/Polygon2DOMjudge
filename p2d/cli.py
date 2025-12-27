import logging
import re
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.logging import RichHandler

from ._version import __version__
from .models import GlobalConfig
from .p2d import DEFAULT_COLOR, ConvertOptions, DomjudgeOptions, convert
from .utils import load_config

app = typer.Typer(pretty_exceptions_show_locals=False)


def version_callback(value: bool | None) -> None:
    if value:
        typer.echo(f"Polygon Package to Domjudge Package v{__version__}")
        raise typer.Exit


def validate_external_id(value: str | None) -> str | None:
    if value is None or re.match(r"^[a-zA-Z0-9-_]+$", value):
        return value
    msg = "external-id must contain only letters, numbers, hyphens and underscores"
    raise typer.BadParameter(msg)


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
        bool | None,
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
        Path | None,
        typer.Option("-o", "--output", help="path of the output package"),
    ] = None,
    global_config_file: Annotated[
        Path | None,
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
        bool,
        typer.Option("--default", help="force use the default output validator."),
    ] = False,
    validator_flags: Annotated[
        str | None,
        typer.Option(help='add some flags to the output validator, only works when "--default" is set.'),
    ] = None,
    memory_limit: Annotated[
        int | None,
        typer.Option(
            help="override the memory limit for DOMjudge package (in MB), default is using the memory limit defined in polygon package, -1 means use DOMjudge default",
        ),
    ] = None,
    output_limit: Annotated[
        int,
        typer.Option(
            help="override the output limit for DOMjudge package (in MB), default is using the default output limit in DOMjudge setting, -1 means use DOMjudge default",
        ),
    ] = -1,
    hide_sample: Annotated[
        bool,
        typer.Option(
            help="hide the sample input and output from the problem statement, no sample data will be available for the contestants (force True if this is an interactive problem).",
        ),
    ] = False,
    keep_sample: Annotated[
        list[int] | None,
        typer.Option(
            "--keep",
            "--keep-sample",
            help="keep the specified numbered sample output from the main and correct solution, can be used multiple times, (e.g. --keep 1 --keep 2), default is replacing all sample output with problem statement.",
        ),
    ] = None,
    external_id: Annotated[
        str | None,
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
        str | None,
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
        msg = 'Cannot use "--default" and "--auto" at the same time.'
        raise typer.BadParameter(msg)

    if skip_confirmation:

        def confirm() -> bool:
            return True
    else:

        def confirm() -> bool:
            return typer.confirm("Are you sure to convert the package?", abort=True, default=True, err=True)

    keep_sample_tuple = tuple(keep_sample) if keep_sample else None

    options = ConvertOptions(
        output=output,
        global_config=global_config,
        options=DomjudgeOptions(
            color=color,
            force_default_validator=force_default_validator,
            auto_detect_std_checker=auto_detect_std_checker,
            validator_flags=validator_flags,
            hide_sample=hide_sample,
            keep_sample=keep_sample_tuple,
            external_id=external_id,
            with_statement=with_statement,
            with_attachments=with_attachments,
            memory_limit_override=memory_limit,
            output_limit_override=output_limit,
        ),
        testset_name=testset_name,
    )

    logger.info(
        "This is Polygon2DOMjudge by cubercsl.\nProcess Polygon Package to DOMjudge Package.\nVersion: %s",
        __version__,
    )
    try:
        convert(
            package=package,
            short_name=short_name,
            options=options,
            confirm=confirm,
        )
    except Exception as e:
        logger.exception(e)
        raise
