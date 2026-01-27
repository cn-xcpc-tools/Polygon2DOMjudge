"""Polygon2DOMjudge - Convert Polygon packages to DOMjudge format.

This package provides tools for converting competitive programming problems
from Polygon format to DOMjudge format.

Main entry points:
    - convert(): High-level function for package conversion
    - Polygon2DOMjudge: Class for detailed control over conversion

Configuration classes:
    - DomjudgeOptions: User-facing options for conversion
    - ConvertOptions: Bundle of options for convert()
    - GlobalConfig: Global settings loaded from config.toml

Pipeline classes (for advanced customization):
    - ProcessPipeline: Sequential processing pipeline
    - ProcessStep: Individual step in the pipeline
    - ProcessingContext: Context passed to pipeline steps
    - DomjudgeProfile: Derived profile for internal processing

Example:
    >>> from p2d import convert, ConvertOptions, DomjudgeOptions
    >>> convert(
    ...     "problem.zip",
    ...     short_name="A",
    ...     options=ConvertOptions(
    ...         options=DomjudgeOptions(color="#FF0000")
    ...     ),
    ... )
"""

from .exceptions import ProcessError
from .models import DEFAULT_COLOR, DomjudgeOptions, GlobalConfig
from .p2d import ConvertOptions, Polygon2DOMjudge, convert
from .pipeline import DomjudgeProfile, ProcessingContext, ProcessPipeline, ProcessStep

__all__ = [
    # Constants
    "DEFAULT_COLOR",
    # Main API
    "Polygon2DOMjudge",
    "convert",
    # Configuration
    "ConvertOptions",
    "DomjudgeOptions",
    "GlobalConfig",
    # Pipeline (advanced)
    "DomjudgeProfile",
    "ProcessError",
    "ProcessPipeline",
    "ProcessStep",
    "ProcessingContext",
]
