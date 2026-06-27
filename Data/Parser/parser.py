"""
PlantUML Parser

The main parser that converts PlantUML class diagram strings into structured
ParsedModel objects. Designed to handle all syntax patterns found in the dataset.

Key features:
- Strict mode: Raises on unrecognized syntax (for iterative development)
- Handles all relationship types with cardinalities and labels
- Supports explicit class/enum definitions
- Handles abstract classes, nested enums, notes

Usage:
    parser = PlantUMLParser(strict=True)
    model = parser.parse(plantuml_string)
"""

import re
from typing import List, Optional, Tuple, Set
from dataclasses import dataclass

from .models import (
    ParsedAttribute,
    ParsedClass,
    ParsedEnum,
    ParsedRelationship,
    ParsedNote,
    ParsedModel,
    RelationshipType,
)
from .tokenizer import (
    extract_uml_blocks,
    remove_comments,
    Token,
    TokenType,
)


@dataclass
class ParseError:
    """Information about a parsing error."""
    message: str
    line_number: int
    line_content: str
    context: List[str]  # Surrounding lines


class PlantUMLParser:
    """
    Parser for PlantUML class diagrams.

    Args:
        strict: If True, raises ValueError on unrecognized syntax.
                If False, logs warnings but continues parsing.
    """

    # Regex pattern for class/enum identifier
    IDENTIFIER = r"[A-Za-z_][A-Za-z0-9_]*"

    # Cardinality patterns - also handle malformed unclosed quotes
    CARDINALITY = r'"([^"]*)"?'

    def __init__(self, strict: bool = True):
        self.strict = strict
        self._errors: List[ParseError] = []
        self._warnings: List[str] = []
        self._current_line: int = 0
        self._lines: List[str] = []

    def parse(self, uml_string: str) -> ParsedModel:
        """
        Parse a PlantUML string into a ParsedModel.

        Args:
            uml_string: Complete PlantUML string with @startuml/@enduml markers.

        Returns:
            ParsedModel containing all extracted elements.

        Raises:
            ValueError: If strict mode and unrecognized syntax encountered.
        """
        self._errors = []
        self._warnings = []

        # Extract UML block
        blocks = extract_uml_blocks(uml_string)
        if not blocks:
            raise ValueError("No UML block found (missing @startuml/@enduml)")

        block = blocks[0]

        # Remove comments
        cleaned, _comments = remove_comments(block)

        # Split into lines and track for error reporting
        self._lines = cleaned.split('\n')

        # Initialize result containers
        classes: List[ParsedClass] = []
        enums: List[ParsedEnum] = []
        relationships: List[ParsedRelationship] = []
        notes: List[ParsedNote] = []
        mentioned_classes: Set[str] = set()

        # Parse line by line with state tracking
        i = 0
        while i < len(self._lines):
            self._current_line = i + 1  # 1-indexed
            line = self._lines[i].strip()

            # Skip empty lines and markers
            if not line or line.startswith('@startuml') or line.startswith('@enduml'):
                i += 1
                continue

            # Try to parse as various constructs
            parsed = False

            # 1. Abstract class definition
            if not parsed:
                result = self._try_parse_class(i, is_abstract=True)
                if result:
                    cls, new_i = result
                    classes.append(cls)
                    i = new_i
                    parsed = True

            # 2. Regular class definition
            if not parsed:
                result = self._try_parse_class(i, is_abstract=False)
                if result:
                    cls, new_i = result
                    classes.append(cls)
                    i = new_i
                    parsed = True

            # 3. Enum definition
            if not parsed:
                result = self._try_parse_enum(i)
                if result:
                    enum, new_i = result
                    enums.append(enum)
                    i = new_i
                    parsed = True

            # 4. Note
            if not parsed:
                result = self._try_parse_note(i)
                if result:
                    note, new_i = result
                    notes.append(note)
                    i = new_i
                    parsed = True

            # 5. Relationship
            if not parsed:
                result = self._try_parse_relationship(line)
                if result:
                    rel, class_names = result
                    relationships.append(rel)
                    mentioned_classes.update(class_names)
                    i += 1
                    parsed = True

            # 6. Standalone attribute (ClassName : attributeName pattern from old format)
            if not parsed:
                result = self._try_parse_standalone_attribute(line)
                if result:
                    class_name, attr = result
                    # Add to existing class or create implicit one
                    existing = next((c for c in classes if c.name == class_name), None)
                    if existing:
                        existing.attributes.append(attr)
                    else:
                        # Create a new class for this attribute
                        classes.append(ParsedClass(
                            name=class_name,
                            is_abstract=False,
                            attributes=[attr]
                        ))
                    mentioned_classes.add(class_name)
                    i += 1
                    parsed = True

            # If nothing parsed and strict mode, raise error
            if not parsed:
                if self.strict:
                    context = self._get_context(i)
                    raise ValueError(
                        f"Unrecognized line {self._current_line}: '{line}'\n"
                        f"Context:\n{chr(10).join(context)}"
                    )
                else:
                    self._warnings.append(f"Line {self._current_line}: Skipped '{line}'")
                    i += 1

        # Compute implicit classes (mentioned in relationships but not defined)
        defined_class_names = {c.name for c in classes}
        implicit_classes = sorted(mentioned_classes - defined_class_names)

        return ParsedModel(
            classes=classes,
            enums=enums,
            relationships=relationships,
            notes=notes,
            raw_source=uml_string,
            implicit_classes=implicit_classes,
        )

    def _get_context(self, line_index: int, context_size: int = 2) -> List[str]:
        """Get surrounding lines for error context."""
        start = max(0, line_index - context_size)
        end = min(len(self._lines), line_index + context_size + 1)

        context = []
        for i in range(start, end):
            marker = ">>> " if i == line_index else "    "
            context.append(f"{marker}{i + 1}: {self._lines[i]}")
        return context

    def _try_parse_class(
        self, start_index: int, is_abstract: bool
    ) -> Optional[Tuple[ParsedClass, int]]:
        """
        Try to parse a class definition starting at the given index.

        Returns (ParsedClass, new_index) or None if not a class definition.
        """
        line = self._lines[start_index].strip()

        # Match class definition
        if is_abstract:
            pattern = rf'^abstract\s+class\s+({self.IDENTIFIER})\s*(\{{)?(.*)$'
        else:
            pattern = rf'^class\s+({self.IDENTIFIER})\s*(\{{)?(.*)$'

        match = re.match(pattern, line, re.IGNORECASE)
        if not match:
            return None

        class_name = match.group(1)
        has_brace = match.group(2) is not None
        rest = match.group(3).strip() if match.group(3) else ""

        attributes: List[ParsedAttribute] = []
        nested_enums: List[ParsedEnum] = []

        # Case 1: Empty class on single line: class Name {} or class Name
        if rest == '}' or (not has_brace and not rest):
            return ParsedClass(class_name, is_abstract, [], []), start_index + 1

        # Case 2: Single-line class with content: class Name { attr1; attr2 }
        if has_brace and '}' in rest:
            content = rest.rstrip('}').strip()
            if content:
                # Parse inline attributes
                for part in content.split(';'):
                    part = part.strip()
                    if part:
                        attr = self._parse_attribute_line(part)
                        if attr:
                            attributes.append(attr)
            return ParsedClass(class_name, is_abstract, attributes, nested_enums), start_index + 1

        # Case 3: Multi-line class definition
        if has_brace:
            i = start_index + 1
            while i < len(self._lines):
                content_line = self._lines[i].strip()

                # End of class
                if content_line == '}':
                    return ParsedClass(class_name, is_abstract, attributes, nested_enums), i + 1

                # Skip empty lines
                if not content_line:
                    i += 1
                    continue

                # Check for nested enum
                nested_enum_result = self._try_parse_nested_enum(i)
                if nested_enum_result:
                    nested_enum, new_i = nested_enum_result
                    nested_enums.append(nested_enum)
                    i = new_i
                    continue

                # Parse as attribute
                attr = self._parse_attribute_line(content_line)
                if attr:
                    attributes.append(attr)

                i += 1

            # If we reach here, class wasn't closed properly
            if self.strict:
                raise ValueError(f"Class '{class_name}' at line {start_index + 1} not properly closed")

            return ParsedClass(class_name, is_abstract, attributes, nested_enums), i

        return None

    def _try_parse_nested_enum(self, start_index: int) -> Optional[Tuple[ParsedEnum, int]]:
        """
        Try to parse a nested enum inside a class.

        Handles: enum EnumName { val1, val2 }
        """
        line = self._lines[start_index].strip()

        # Inline enum pattern
        inline_pattern = rf'^enum\s+({self.IDENTIFIER})\s*\{{\s*([^}}]+)\s*\}}$'
        inline_match = re.match(inline_pattern, line)
        if inline_match:
            enum_name = inline_match.group(1)
            values_str = inline_match.group(2)
            values = [v.strip() for v in values_str.split(',') if v.strip()]
            return ParsedEnum(enum_name, values, is_inline=True), start_index + 1

        return None

    def _try_parse_enum(self, start_index: int) -> Optional[Tuple[ParsedEnum, int]]:
        """
        Try to parse an enum definition.

        Returns (ParsedEnum, new_index) or None.
        """
        line = self._lines[start_index].strip()

        # Inline enum: enum Name { val1, val2 }
        inline_pattern = rf'^enum\s+({self.IDENTIFIER})\s*\{{\s*([^}}]+)\s*\}}$'
        inline_match = re.match(inline_pattern, line)
        if inline_match:
            enum_name = inline_match.group(1)
            values_str = inline_match.group(2)
            values = [v.strip() for v in values_str.split(',') if v.strip()]
            return ParsedEnum(enum_name, values, is_inline=True), start_index + 1

        # Multi-line enum: enum Name {
        multiline_pattern = rf'^enum\s+({self.IDENTIFIER})\s*\{{'
        multiline_match = re.match(multiline_pattern, line)
        if multiline_match:
            enum_name = multiline_match.group(1)
            values: List[str] = []

            i = start_index + 1
            while i < len(self._lines):
                content_line = self._lines[i].strip()

                # End of enum
                if content_line == '}':
                    return ParsedEnum(enum_name, values, is_inline=False), i + 1

                # Skip empty lines
                if not content_line:
                    i += 1
                    continue

                # Parse enum value (simple identifier or ellipsis)
                value_pattern = rf'^({self.IDENTIFIER}|\.\.\.)\s*$'
                value_match = re.match(value_pattern, content_line)
                if value_match:
                    values.append(value_match.group(1))

                i += 1

            # Enum not properly closed
            if self.strict:
                raise ValueError(f"Enum '{enum_name}' at line {start_index + 1} not properly closed")

            return ParsedEnum(enum_name, values, is_inline=False), i

        return None

    def _try_parse_note(self, start_index: int) -> Optional[Tuple[ParsedNote, int]]:
        """
        Try to parse a note block.

        Returns (ParsedNote, new_index) or None.
        """
        line = self._lines[start_index].strip()

        note_pattern = r'^note\s+(.+)$'
        match = re.match(note_pattern, line, re.IGNORECASE)
        if not match:
            return None

        position = match.group(1)
        content_lines = []

        i = start_index + 1
        while i < len(self._lines):
            content_line = self._lines[i].strip()

            if content_line.lower() == 'end note':
                content = '\n'.join(content_lines)
                return ParsedNote(content, position), i + 1

            content_lines.append(content_line)
            i += 1

        # Note not closed - might be single line note
        # Some notes are just "note right of X : content"
        if ':' in position:
            parts = position.split(':', 1)
            return ParsedNote(parts[1].strip(), parts[0].strip()), start_index + 1

        if self.strict:
            raise ValueError(f"Note at line {start_index + 1} not properly closed")

        content = '\n'.join(content_lines)
        return ParsedNote(content, position), i

    def _try_parse_relationship(
        self, line: str
    ) -> Optional[Tuple[ParsedRelationship, Set[str]]]:
        """
        Try to parse a relationship line.

        Returns (ParsedRelationship, set of class names) or None.
        """
        # Association class pattern: (Class1, Class2) .. Class3
        assoc_class_pattern = rf'^\(({self.IDENTIFIER})\s*,\s*({self.IDENTIFIER})\)\s*\.\.\s*({self.IDENTIFIER})(?:\s*:\s*(.+))?$'
        assoc_match = re.match(assoc_class_pattern, line)
        if assoc_match:
            class1 = assoc_match.group(1)
            class2 = assoc_match.group(2)
            assoc_class = assoc_match.group(3)
            label = assoc_match.group(4).strip() if assoc_match.group(4) else None

            return ParsedRelationship(
                source=f"({class1}, {class2})",
                target=assoc_class,
                relationship_type=RelationshipType.ASSOCIATION_CLASS,
                label=label,
                association_members=(class1, class2),
            ), {class1, class2, assoc_class}

        # Standard relationship patterns
        # Format: Source "card" ARROW "card" Target : label

        # Define arrow patterns and their types
        # Order matters! More specific patterns must come before less specific ones
        arrow_patterns = [
            # Inheritance arrows
            (r'<\|--', RelationshipType.INHERITANCE, 'left'),      # Parent <|-- Child
            (r'--\|>', RelationshipType.INHERITANCE, 'right'),     # Child --|> Parent
            (r'<\|-', RelationshipType.INHERITANCE, 'left'),       # Parent <|- Child (single dash)
            (r'-\|>', RelationshipType.INHERITANCE, 'right'),      # Child -|> Parent (single dash)
            # Directed composition (must be before regular composition)
            (r'\*-->', RelationshipType.COMPOSITION, 'right'),     # Composite *--> Part (directed)
            (r'<--\*', RelationshipType.COMPOSITION, 'left'),      # Part <--* Composite (directed)
            # Regular composition
            (r'\*--', RelationshipType.COMPOSITION, 'left'),       # Composite *-- Part
            (r'--\*', RelationshipType.COMPOSITION, 'right'),      # Part --* Composite
            # Directed aggregation (must be before regular aggregation)
            (r'o-->', RelationshipType.AGGREGATION, 'right'),      # Whole o--> Part (directed)
            (r'<--o', RelationshipType.AGGREGATION, 'left'),       # Part <--o Whole (directed)
            # Regular aggregation
            (r'o--', RelationshipType.AGGREGATION, 'left'),        # Whole o-- Part
            (r'--o', RelationshipType.AGGREGATION, 'right'),       # Part --o Whole
            # Directed association
            (r'-->', RelationshipType.DIRECTED_ASSOCIATION, 'right'),  # A --> B
            (r'<--', RelationshipType.DIRECTED_ASSOCIATION, 'left'),   # A <-- B
            (r'->', RelationshipType.DIRECTED_ASSOCIATION, 'right'),   # A -> B (single dash)
            (r'<-', RelationshipType.DIRECTED_ASSOCIATION, 'left'),    # A <- B (single dash)
            # Dependency
            (r'\.\.', RelationshipType.DEPENDENCY, None),          # A .. B
            # Basic association
            (r'--', RelationshipType.ASSOCIATION, None),           # A -- B
            (r'-', RelationshipType.ASSOCIATION, None),            # A - B (single dash)
        ]

        for arrow_pattern, rel_type, direction in arrow_patterns:
            # Build full pattern with optional cardinalities and label
            full_pattern = (
                rf'^({self.IDENTIFIER})\s*'
                rf'(?:{self.CARDINALITY}\s*)?'
                rf'({arrow_pattern})\s*'
                rf'(?:{self.CARDINALITY}\s*)?'
                rf'({self.IDENTIFIER})'
                rf'(?:\s*:\s*(.+))?$'
            )

            match = re.match(full_pattern, line)
            if match:
                source = match.group(1)
                source_card = match.group(2)
                # match.group(3) is the arrow
                target_card = match.group(4)
                target = match.group(5)
                label = match.group(6).strip() if match.group(6) else None

                # Handle directionality based on relationship type
                # The 'direction' field has different meanings:
                # - For directed associations: which way the arrow points
                # - For inheritance: which side has the triangle
                # - For composition/aggregation: which side has the diamond
                #
                # We normalize so that:
                # - Inheritance: parent is always source
                # - Composition/Aggregation: composite/whole is always source
                # - Directed association: arrow points from source to target

                if rel_type == RelationshipType.INHERITANCE:
                    if direction == 'right':
                        # Child --|> Parent -> swap so Parent is source
                        source, target = target, source
                        source_card, target_card = target_card, source_card
                    # direction == 'left': Parent <|-- Child -> already correct

                elif rel_type in (RelationshipType.COMPOSITION, RelationshipType.AGGREGATION):
                    if direction == 'right':
                        # Part --* Composite or Part --o Whole -> swap so Composite/Whole is source
                        source, target = target, source
                        source_card, target_card = target_card, source_card
                    # direction == 'left': Composite *-- Part -> already correct

                elif rel_type == RelationshipType.DIRECTED_ASSOCIATION:
                    if direction == 'left':
                        # A <-- B means B points to A -> swap so B is source
                        source, target = target, source
                        source_card, target_card = target_card, source_card
                    # direction == 'right': A --> B -> already correct

                return ParsedRelationship(
                    source=source,
                    target=target,
                    relationship_type=rel_type,
                    source_cardinality=source_card,
                    target_cardinality=target_card,
                    label=label,
                ), {source, target}

        return None

    def _try_parse_standalone_attribute(
        self, line: str
    ) -> Optional[Tuple[str, ParsedAttribute]]:
        """
        Try to parse a standalone attribute line: ClassName : attributeName

        This is the old PlantUML syntax where attributes are defined outside class blocks.

        Returns (class_name, ParsedAttribute) or None.
        """
        pattern = rf'^({self.IDENTIFIER})\s*:\s*({self.IDENTIFIER})$'
        match = re.match(pattern, line)
        if match:
            class_name = match.group(1)
            attr_name = match.group(2)
            return class_name, ParsedAttribute(name=attr_name)

        return None

    def _parse_attribute_line(self, line: str) -> Optional[ParsedAttribute]:
        """
        Parse an attribute line within a class body.

        Handles:
        - name                           (untyped)
        - name : Type                    (UML style)
        - name : Type = default          (UML style with default)
        - Type name                      (Java/C++ style)
        - Type name = default            (Java/C++ style with default)
        - const Type name = value        (constant)
        """
        line = line.strip()

        # Skip lines that look like nested enums
        if line.startswith('enum '):
            return None

        # Constant pattern: const Type name = value
        const_pattern = rf'^const\s+({self.IDENTIFIER})\s+({self.IDENTIFIER})\s*=\s*(.+)$'
        const_match = re.match(const_pattern, line)
        if const_match:
            attr_type = const_match.group(1)
            attr_name = const_match.group(2)
            default_value = const_match.group(3).strip()
            return ParsedAttribute(
                name=attr_name,
                type=attr_type,
                default_value=default_value,
                is_constant=True
            )

        # UML style: name : Type = default
        uml_pattern = rf'^({self.IDENTIFIER})\s*:\s*([\w\[\]<>,\s]+?)(?:\s*=\s*(.+))?$'
        uml_match = re.match(uml_pattern, line)
        if uml_match:
            attr_name = uml_match.group(1)
            attr_type = uml_match.group(2).strip()
            default_value = uml_match.group(3).strip() if uml_match.group(3) else None
            return ParsedAttribute(
                name=attr_name,
                type=attr_type,
                default_value=default_value,
                is_constant=False
            )

        # Java/C++ style: Type name = default (must have at least two words)
        java_pattern = rf'^({self.IDENTIFIER})\s+({self.IDENTIFIER})(?:\s*=\s*(.+))?$'
        java_match = re.match(java_pattern, line)
        if java_match:
            attr_type = java_match.group(1)
            attr_name = java_match.group(2)
            default_value = java_match.group(3).strip() if java_match.group(3) else None
            return ParsedAttribute(
                name=attr_name,
                type=attr_type,
                default_value=default_value,
                is_constant=False
            )

        # Simple attribute: just name (single identifier)
        simple_pattern = rf'^({self.IDENTIFIER})$'
        simple_match = re.match(simple_pattern, line)
        if simple_match:
            return ParsedAttribute(name=simple_match.group(1))

        return None

    @property
    def errors(self) -> List[ParseError]:
        """Get list of parsing errors."""
        return self._errors

    @property
    def warnings(self) -> List[str]:
        """Get list of warnings (when strict=False)."""
        return self._warnings
