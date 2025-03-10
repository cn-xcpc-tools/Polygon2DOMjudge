import logging
import xml.etree.ElementTree

from pathlib import Path
from typing import Annotated, Optional

from rich.logging import RichHandler
import typer

from ._version import __version__


app = typer.Typer(pretty_exceptions_show_locals=False)


def version_callback(value: Optional[bool]) -> None:
    if value:
        typer.echo(f"Polygon Package to Domjudge Package v{__version__}")
        raise typer.Exit()


def problem_index_and_name(problem):
    return problem.attrib["index"], problem.attrib["url"].split("/")[-1]


@app.command(help="Generate p2d command line arguments from contest.xml.")
def convert_contest(
    contest_xml: Annotated[Path, typer.Argument(help="path of the contest.xml file")],
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
        level=log_level.upper(), format="%(message)s", datefmt="[%X]", handlers=[RichHandler(rich_tracebacks=True)]
    )
    logger = logging.getLogger(__name__)

    try:
        tree = xml.etree.ElementTree.parse(contest_xml)
        root = tree.getroot()
        problems = root.find("problems")
        if problems is None:
            logger.error("No problems found in contest.xml")
            raise ValueError("No problems found in contest.xml")
        logger.info("Found %d problems in %s", len(problems), str(contest_xml))
        print("#!/bin/bash")
        print("POLYGON_PACKAGE_DIR=polygon      # change this to the polygon package directory")
        print("DOMJUDGE_PACKAGE_DIR=domjudge    # change this to the domjudge package directory")
        print()
        for problem in problems:
            index, name = problem_index_and_name(problem)
            logger.info("Problem %s: %s", index, name)
            print(f"""# Problem {index}: {name} (change the color if needed)
p2d --yes --code {index} --color "#FF0000" \\
    --output "$DOMJUDGE_PACKAGE_DIR/{name}.zip" --auto \\
    "$POLYGON_PACKAGE_DIR/{name}-*\\$linux.zip"
""")
    except Exception as e:
        logger.error(e)
        raise


def main():  # pragma: no cover
    app()


if __name__ == "__main__":
    main()
