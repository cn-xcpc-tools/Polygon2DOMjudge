import logging
import xml.etree.ElementTree
from pathlib import Path
from typing import Annotated
from xml.etree.ElementTree import Element

import typer
from rich.console import Console
from rich.logging import RichHandler

from ._version import __version__

app = typer.Typer(pretty_exceptions_show_locals=False)


def version_callback(value: bool | None) -> None:
    if value:
        typer.echo(f"Polygon Package to Domjudge Package v{__version__}")
        raise typer.Exit


def problem_index_and_name(problem: Element) -> tuple[str, str]:
    return problem.attrib["index"], problem.attrib["url"].split("/")[-1]


@app.command(help="Generate p2d command line arguments from contest.xml.")
def convert_contest(
    contest_xml: Annotated[Path, typer.Argument(help="path of the contest.xml file")],
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
    log_level: Annotated[
        str,
        typer.Option(
            "-l",
            "--log-level",
            help="set log level (debug, info, warning, error, critical)",
        ),
    ] = "info",
) -> None:
    logging.basicConfig(
        level=log_level.upper(),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, console=Console(stderr=True))],
    )
    logger = logging.getLogger(__name__)

    try:
        tree = xml.etree.ElementTree.parse(contest_xml)
        root = tree.getroot()
        problems = root.find("problems")
        if problems is None:
            msg = "No problems found in contest.xml"
            raise ValueError(msg)
        logger.info("Found %d problems in %s", len(problems), str(contest_xml))
        for problem in problems:
            index, name = problem_index_and_name(problem)
            logger.info("Problem %s: %s", index, name)
    except Exception as e:
        logger.exception(e)
        raise


if __name__ == "__main__":
    app()
