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
