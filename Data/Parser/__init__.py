"""
PlantUML Parser Module

A robust parser for PlantUML class diagrams that handles all syntax patterns
found in the dataset. Designed for iterative development with test harness.

Example usage:
    from Data.Parser import PlantUMLParser, ParsedModel

    parser = PlantUMLParser(strict=True)
    model = parser.parse(plantuml_string)

    print(f"Classes: {len(model.classes)}")
    print(f"Enums: {len(model.enums)}")
    print(f"Relationships: {len(model.relationships)}")
"""

from .models import (
    ParsedAttribute,
    ParsedClass,
    ParsedEnum,
    ParsedRelationship,
    ParsedNote,
    ParsedModel,
)
from .parser import PlantUMLParser
from .test_runner import ParserTestRunner
from .test_report import TestResult, TestReport

__all__ = [
    # Data models
    "ParsedAttribute",
    "ParsedClass",
    "ParsedEnum",
    "ParsedRelationship",
    "ParsedNote",
    "ParsedModel",
    # Parser
    "PlantUMLParser",
    # Test infrastructure
    "ParserTestRunner",
    "TestResult",
    "TestReport",
]
