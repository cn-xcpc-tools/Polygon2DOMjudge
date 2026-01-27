"""Processing steps for Polygon to DOMjudge package conversion.

Each step is a function that takes a ProcessingContext and performs
a specific transformation or file generation task.

Steps:
    add_metadata: Generate domjudge-problem.ini, problem.yaml, and validators
    add_testcases: Copy test cases into sample/secret directories
    add_jury_solutions: Copy jury solutions with expected verdict annotations
    add_statement: Copy the problem statement PDF
    add_attachments: Copy additional attachments
    make_archive: Create the final zip archive
"""

from .archive import make_archive
from .attachments import add_attachments
from .jury_solutions import add_jury_solutions
from .metadata import add_metadata
from .statement import add_statement
from .testcases import add_testcases

__all__ = [
    "add_attachments",
    "add_jury_solutions",
    "add_metadata",
    "add_statement",
    "add_testcases",
    "make_archive",
]
