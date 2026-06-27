"""
Data Models for Parsed PlantUML Elements

This module defines dataclasses representing the structured output of
parsing PlantUML class diagrams. Each class corresponds to a UML element
type that can appear in the diagrams.

The hierarchy is:
    ParsedModel
    ├── classes: List[ParsedClass]
    │   ├── attributes: List[ParsedAttribute]
    │   └── nested_enums: List[ParsedEnum]
    ├── enums: List[ParsedEnum]
    ├── relationships: List[ParsedRelationship]
    └── notes: List[ParsedNote]
"""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class RelationshipType(Enum):
    """Types of relationships between classes in UML."""
    ASSOCIATION = "association"           # --
    DIRECTED_ASSOCIATION = "directed"     # -->
    INHERITANCE = "inheritance"           # <|--
    COMPOSITION = "composition"           # *--
    AGGREGATION = "aggregation"           # o--
    DEPENDENCY = "dependency"             # ..
    ASSOCIATION_CLASS = "association_class"  # (A, B) .. C


@dataclass
class ParsedAttribute:
    """
    Represents an attribute within a class.

    Examples:
        - `name` -> name="name", type=None, default=None
        - `name : String` -> name="name", type="String", default=None
        - `status : Status = Active` -> name="status", type="Status", default="Active"
        - `const Integer MAX = 10` -> name="MAX", type="Integer", default="10", is_constant=True
    """
    name: str
    type: Optional[str] = None
    default_value: Optional[str] = None
    is_constant: bool = False

    def __str__(self) -> str:
        parts = [self.name]
        if self.type:
            parts.append(f": {self.type}")
        if self.default_value:
            parts.append(f"= {self.default_value}")
        if self.is_constant:
            return f"const {' '.join(parts)}"
        return " ".join(parts)


@dataclass
class ParsedEnum:
    """
    Represents an enumeration definition.

    Examples:
        Block format:
            enum Status {
                Active
                Inactive
            }

        Inline format (inside class):
            enum DeviceStatus { Activated, Deactivated }
    """
    name: str
    values: List[str] = field(default_factory=list)
    is_inline: bool = False  # True if defined inline inside a class

    def __str__(self) -> str:
        if self.is_inline:
            return f"enum {self.name} {{ {', '.join(self.values)} }}"
        return f"enum {self.name} {{ {', '.join(self.values)} }}"


@dataclass
class ParsedClass:
    """
    Represents a class definition with its attributes and nested enums.

    Classes can be defined explicitly:
        class Person {
            name : String
            age : Integer
        }

    Or abstractly:
        abstract class PersonRole {
            idNumber
        }

    Classes may also contain nested enum definitions (rare but exists in SHAS model).
    """
    name: str
    is_abstract: bool = False
    attributes: List[ParsedAttribute] = field(default_factory=list)
    nested_enums: List[ParsedEnum] = field(default_factory=list)

    def __str__(self) -> str:
        prefix = "abstract class" if self.is_abstract else "class"
        return f"{prefix} {self.name}"


@dataclass
class ParsedRelationship:
    """
    Represents a relationship between two classes.

    Examples:
        - `Person "1" -- "*" Address` (association)
        - `Person "1" --> "*" Order : places` (directed association with label)
        - `Animal <|-- Dog` (inheritance)
        - `Car "1" *-- "4" Wheel` (composition)
        - `Department "1" o-- "*" Employee` (aggregation)
        - `(Student, Course) .. Enrollment` (association class)
    """
    source: str
    target: str
    relationship_type: RelationshipType
    source_cardinality: Optional[str] = None
    target_cardinality: Optional[str] = None
    label: Optional[str] = None

    # For association classes: the classes being associated
    association_members: Optional[tuple] = None  # (Class1, Class2) for association class

    def __str__(self) -> str:
        arrow_map = {
            RelationshipType.ASSOCIATION: "--",
            RelationshipType.DIRECTED_ASSOCIATION: "-->",
            RelationshipType.INHERITANCE: "<|--",
            RelationshipType.COMPOSITION: "*--",
            RelationshipType.AGGREGATION: "o--",
            RelationshipType.DEPENDENCY: "..",
            RelationshipType.ASSOCIATION_CLASS: "..",
        }
        arrow = arrow_map.get(self.relationship_type, "--")

        parts = [self.source]
        if self.source_cardinality:
            parts.append(f'"{self.source_cardinality}"')
        parts.append(arrow)
        if self.target_cardinality:
            parts.append(f'"{self.target_cardinality}"')
        parts.append(self.target)
        if self.label:
            parts.append(f": {self.label}")

        return " ".join(parts)


@dataclass
class ParsedNote:
    """
    Represents a note annotation in the diagram.

    Example:
        note right of Doctor
        This is a multi-line
        note explaining something.
        end note
    """
    content: str
    position: Optional[str] = None  # "right of Doctor", "left of Person", etc.

    def __str__(self) -> str:
        if self.position:
            return f"note {self.position}: {self.content[:50]}..."
        return f"note: {self.content[:50]}..."


@dataclass
class ParsedModel:
    """
    The complete parsed representation of a PlantUML class diagram.

    Contains all extracted elements from the UML source:
    - Explicitly defined classes (with attributes and nested enums)
    - Standalone enum definitions
    - All relationships between classes
    - Notes and annotations
    - The original raw source for reference

    Classes that are only mentioned in relationships (not explicitly defined)
    are tracked separately in `implicit_classes`.
    """
    classes: List[ParsedClass] = field(default_factory=list)
    enums: List[ParsedEnum] = field(default_factory=list)
    relationships: List[ParsedRelationship] = field(default_factory=list)
    notes: List[ParsedNote] = field(default_factory=list)
    raw_source: str = ""

    # Classes mentioned in relationships but not explicitly defined
    implicit_classes: List[str] = field(default_factory=list)

    @property
    def all_class_names(self) -> List[str]:
        """Get all class names (both explicit and implicit)."""
        explicit = [c.name for c in self.classes]
        return sorted(set(explicit + self.implicit_classes))

    @property
    def all_enum_names(self) -> List[str]:
        """Get all enum names (standalone and nested)."""
        standalone = [e.name for e in self.enums]
        nested = [e.name for c in self.classes for e in c.nested_enums]
        return sorted(set(standalone + nested))

    def get_class(self, name: str) -> Optional[ParsedClass]:
        """Get a class by name, or None if not found."""
        for c in self.classes:
            if c.name == name:
                return c
        return None

    def get_enum(self, name: str) -> Optional[ParsedEnum]:
        """Get an enum by name (searches standalone and nested)."""
        for e in self.enums:
            if e.name == name:
                return e
        for c in self.classes:
            for e in c.nested_enums:
                if e.name == name:
                    return e
        return None

    def summary(self) -> str:
        """Return a brief summary of the parsed model."""
        return (
            f"ParsedModel: {len(self.classes)} classes, "
            f"{len(self.enums)} enums, "
            f"{len(self.relationships)} relationships, "
            f"{len(self.implicit_classes)} implicit classes"
        )

    def __str__(self) -> str:
        return self.summary()
