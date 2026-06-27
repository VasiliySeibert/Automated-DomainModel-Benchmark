#!/usr/bin/env python3
"""
Qualitative Testing Script for PlantUML Parser

Takes a numeric index (0-46) and displays:
1. The original PlantUML string from the dataset
2. The parsed representation

Usage:
    python qualitative_test.py <index>

    # Example:
    python qualitative_test.py 0    # First PlantUML (LabTracker_reference)
    python qualitative_test.py 5    # Sixth PlantUML

    # List all available indices:
    python qualitative_test.py --list
"""

import sys
import json
from pathlib import Path
from typing import List, Tuple

# Add project root to path
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from Data.Parser.parser import PlantUMLParser
from Data.Parser.models import ParsedModel

DATASET_PATH = PROJECT_ROOT / "Dataset" / "combined-data.json"
SETTINGS = ['reference', '0shot', '1shot_BTMS', '1shot_H2S', '2shots', 'CoT']


def load_all_plantuml() -> List[Tuple[str, str, str]]:
    """
    Load all PlantUML strings from dataset.

    Returns:
        List of (comparison_id, model_key, plantuml_string) tuples.
    """
    with open(DATASET_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    result = []
    models = data.get('models', {})

    for model_key in models:
        model_data = models[model_key]

        # Reference model
        ref_uml = model_data.get('reference_plantuml', '')
        if ref_uml:
            result.append((f"{model_key}_reference", model_key, ref_uml))

        # Generated models
        generated = model_data.get('generated_plantuml', {})
        for setting in ['0shot', '1shot_BTMS', '1shot_H2S', '2shots', 'CoT']:
            gen_uml = generated.get(setting, '')
            if gen_uml:
                result.append((f"{model_key}_{setting}", model_key, gen_uml))

    return result


def print_separator(char: str = '=', width: int = 80):
    print(char * width)


def print_header(title: str, width: int = 80):
    print_separator('=', width)
    print(f" {title}")
    print_separator('=', width)


def format_parsed_model(model: ParsedModel) -> str:
    """Format the parsed model for display."""
    lines = []

    # Classes
    lines.append(f"\n[CLASSES] ({len(model.classes)} total)")
    for cls in model.classes:
        prefix = "abstract " if cls.is_abstract else ""
        lines.append(f"  {prefix}class {cls.name}")
        for attr in cls.attributes:
            attr_str = f"    - {attr.name}"
            if attr.type:
                attr_str += f" : {attr.type}"
            if attr.default_value:
                attr_str += f" = {attr.default_value}"
            if attr.is_constant:
                attr_str = f"    - const {attr_str.strip('    - ')}"
            lines.append(attr_str)
        for nested_enum in cls.nested_enums:
            lines.append(f"    - enum {nested_enum.name} {{ {', '.join(nested_enum.values)} }}")

    # Enums
    lines.append(f"\n[ENUMS] ({len(model.enums)} total)")
    for enum in model.enums:
        inline = " (inline)" if enum.is_inline else ""
        lines.append(f"  enum {enum.name}{inline}")
        for value in enum.values:
            lines.append(f"    - {value}")

    # Relationships
    lines.append(f"\n[RELATIONSHIPS] ({len(model.relationships)} total)")
    for rel in model.relationships:
        src_card = f' "{rel.source_cardinality}"' if rel.source_cardinality else ''
        tgt_card = f' "{rel.target_cardinality}"' if rel.target_cardinality else ''
        label = f' : {rel.label}' if rel.label else ''

        arrow_map = {
            'association': '--',
            'directed': '-->',
            'inheritance': '<|--',
            'composition': '*--',
            'aggregation': 'o--',
            'dependency': '..',
            'association_class': '..',
        }
        arrow = arrow_map.get(rel.relationship_type.value, '--')

        if rel.association_members:
            src = f"({rel.association_members[0]}, {rel.association_members[1]})"
        else:
            src = rel.source

        lines.append(f"  {src}{src_card} {arrow}{tgt_card} {rel.target}{label}")

    # Implicit classes
    if model.implicit_classes:
        lines.append(f"\n[IMPLICIT CLASSES] ({len(model.implicit_classes)} total)")
        lines.append(f"  {', '.join(model.implicit_classes)}")

    # Notes
    if model.notes:
        lines.append(f"\n[NOTES] ({len(model.notes)} total)")
        for note in model.notes:
            content_preview = note.content[:50] + "..." if len(note.content) > 50 else note.content
            lines.append(f"  - {note.position}: {content_preview}")

    return '\n'.join(lines)


def list_all_indices():
    """Print all available indices and their IDs."""
    all_uml = load_all_plantuml()

    print_header("Available PlantUML Indices")
    print(f"\nTotal: {len(all_uml)} PlantUML strings\n")

    for i, (comp_id, model_key, _) in enumerate(all_uml):
        print(f"  [{i:2d}] {comp_id}")

    print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python qualitative_test.py <index>")
        print("       python qualitative_test.py --list")
        sys.exit(1)

    if sys.argv[1] == '--list':
        list_all_indices()
        sys.exit(0)

    try:
        index = int(sys.argv[1])
    except ValueError:
        print(f"Error: '{sys.argv[1]}' is not a valid index")
        sys.exit(1)

    # Load all PlantUML strings
    all_uml = load_all_plantuml()

    # Support Python-style negative indexing
    if index < 0:
        index = len(all_uml) + index

    if index < 0 or index >= len(all_uml):
        print(f"Error: Index out of range. Valid range: 0-{len(all_uml)-1} (or -1 to -{len(all_uml)})")
        sys.exit(1)

    comp_id, model_key, plantuml = all_uml[index]

    # Parse the PlantUML
    parser = PlantUMLParser(strict=True)
    try:
        parsed = parser.parse(plantuml)
    except Exception as e:
        print(f"Error parsing: {e}")
        sys.exit(1)

    # Display results
    print_header(f"Qualitative Test: [{index}] {comp_id}")

    print(f"\nModel: {model_key}")
    print(f"ID: {comp_id}")
    print(f"Lines: {len(plantuml.splitlines())}")

    # Original PlantUML
    print_header("ORIGINAL PLANTUML", 80)
    print()
    # Add line numbers
    for i, line in enumerate(plantuml.splitlines(), start=1):
        print(f"{i:3d} | {line}")
    print()

    # Parsed representation
    print_header("PARSED REPRESENTATION", 80)
    print(format_parsed_model(parsed))
    print()

    # Summary
    print_header("SUMMARY", 80)
    print(f"\n{parsed.summary()}")
    print()


if __name__ == '__main__':
    main()
