"""
PlantUML Tokenizer

This module handles the initial processing of PlantUML text:
1. Extract UML blocks from raw text
2. Remove/handle comments
3. Group multi-line constructs (class bodies, enum bodies, notes)
4. Return tokenized elements ready for parsing

The tokenizer bridges raw PlantUML text and the structured parser.
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple
from enum import Enum, auto


class TokenType(Enum):
    """Types of tokens that can be extracted from PlantUML."""
    CLASS_START = auto()        # class ClassName {
    CLASS_END = auto()          # }
    ABSTRACT_CLASS_START = auto()  # abstract class ClassName {
    ENUM_START = auto()         # enum EnumName {
    ENUM_END = auto()           # }
    NOTE_START = auto()         # note right of X
    NOTE_END = auto()           # end note
    RELATIONSHIP = auto()       # A -- B, A <|-- B, etc.
    ATTRIBUTE = auto()          # name : Type
    ENUM_VALUE = auto()         # VALUE_NAME
    COMMENT = auto()            # ' comment or // comment
    BLANK = auto()              # Empty line
    UNKNOWN = auto()            # Unrecognized line


@dataclass
class Token:
    """A single token extracted from PlantUML text."""
    type: TokenType
    content: str
    line_number: int
    raw_line: str  # Original line for error reporting


@dataclass
class MultiLineConstruct:
    """
    A grouped multi-line construct (class body, enum body, note).

    Used to group tokens that belong together for easier parsing.
    """
    construct_type: str  # "class", "enum", "note"
    name: Optional[str]  # Class/enum name, None for notes
    is_abstract: bool  # For classes
    content_tokens: List[Token]  # Tokens within the construct
    start_line: int
    end_line: int


def extract_uml_blocks(input_text: str) -> List[str]:
    """
    Extract all UML blocks from input text.

    A UML block is text between @startuml and @enduml markers.

    Args:
        input_text: Raw text that may contain one or more UML blocks.

    Returns:
        List of UML block strings (including the start/end markers).

    Raises:
        ValueError: If no UML blocks found.
    """
    pattern = r"@startuml(.*?)@enduml"
    matches = re.findall(pattern, input_text, flags=re.DOTALL)

    if not matches:
        raise ValueError("No UML blocks found in input (missing @startuml/@enduml markers)")

    blocks = [f"@startuml{match}@enduml" for match in matches]
    return blocks


def remove_comments(text: str) -> Tuple[str, List[Tuple[int, str]]]:
    """
    Remove comments from PlantUML text while preserving line numbers.

    Handles these comment styles:
    - Single quote: ' This is a comment
    - Double slash: // This is a comment
    - Block comment: /' multi-line comment '/
    - Inline block comment: /' comment '/ on same line

    Does NOT remove comments inside strings (though PlantUML rarely has those).

    Args:
        text: PlantUML text with potential comments.

    Returns:
        Tuple of (cleaned text, list of (line_number, comment) tuples).
    """
    # First pass: remove block comments /' ... '/
    # These can span multiple lines
    text, block_comments = _remove_block_comments(text)

    lines = text.split('\n')
    cleaned_lines = []
    comments = list(block_comments)

    for i, line in enumerate(lines, start=1):
        # Check for single-quote comment (PlantUML style)
        # But be careful not to match quotes inside cardinalities like "1" -- "*"
        single_quote_match = re.match(r"^(\s*)'(.*)$", line)
        if single_quote_match:
            comments.append((i, single_quote_match.group(2).strip()))
            cleaned_lines.append("")  # Preserve line number
            continue

        # Check for double-slash comment
        double_slash_match = re.match(r"^(\s*)//(.*)$", line)
        if double_slash_match:
            comments.append((i, double_slash_match.group(2).strip()))
            cleaned_lines.append("")  # Preserve line number
            continue

        # Handle inline comments (rare but possible)
        # Only match ' or // not inside quotes
        # This is a simplification - we strip trailing comments
        inline_single = re.search(r"^([^']*)'(.*)$", line)
        inline_double = re.search(r"^([^/]*)//(.*)$", line)

        if inline_single and not is_inside_quotes(line, inline_single.start(1)):
            cleaned_lines.append(inline_single.group(1).rstrip())
            comments.append((i, inline_single.group(2).strip()))
        elif inline_double:
            cleaned_lines.append(inline_double.group(1).rstrip())
            comments.append((i, inline_double.group(2).strip()))
        else:
            cleaned_lines.append(line)

    return '\n'.join(cleaned_lines), comments


def _remove_block_comments(text: str) -> Tuple[str, List[Tuple[int, str]]]:
    """
    Remove PlantUML block comments (/' ... '/).

    Block comments can span multiple lines. We replace them with blank lines
    to preserve line numbers.

    Args:
        text: Text potentially containing block comments.

    Returns:
        Tuple of (cleaned text, list of (start_line, comment) tuples).
    """
    comments = []
    result = []
    lines = text.split('\n')
    in_block_comment = False
    block_start_line = 0
    block_content = []

    for i, line in enumerate(lines, start=1):
        if not in_block_comment:
            # Check for block comment start
            if "/'" in line:
                # Check if it's a single-line block comment: /' comment '/
                single_line_match = re.match(r"^(.*)/'(.*)'/(.*)$", line)
                if single_line_match:
                    # Remove the comment, keep before and after
                    before = single_line_match.group(1)
                    comment = single_line_match.group(2)
                    after = single_line_match.group(3)
                    result.append(before + after)
                    comments.append((i, comment.strip()))
                else:
                    # Multi-line block comment starts
                    in_block_comment = True
                    block_start_line = i
                    # Keep content before /'
                    before_match = re.match(r"^(.*)/'\s*(.*)$", line)
                    if before_match:
                        result.append(before_match.group(1))
                        block_content = [before_match.group(2)]
                    else:
                        result.append("")
                        block_content = []
            else:
                result.append(line)
        else:
            # Inside block comment
            if "'/" in line:
                # Block comment ends
                after_match = re.match(r"^(.*)'/(.*)$", line)
                if after_match:
                    block_content.append(after_match.group(1))
                    result.append(after_match.group(2))
                else:
                    result.append("")

                comments.append((block_start_line, ' '.join(block_content).strip()))
                in_block_comment = False
                block_content = []
            else:
                # Still inside block comment
                block_content.append(line.strip())
                result.append("")  # Blank line to preserve line numbers

    return '\n'.join(result), comments


def is_inside_quotes(line: str, position: int) -> bool:
    """Check if a position in a line is inside quoted strings."""
    quote_count = 0
    for i, char in enumerate(line[:position]):
        if char == '"':
            quote_count += 1
    return quote_count % 2 == 1


def tokenize_line(line: str, line_number: int) -> Token:
    """
    Classify a single line and return appropriate token.

    Args:
        line: The line content (already stripped of comments).
        line_number: Line number in original source.

    Returns:
        Token with appropriate type and content.
    """
    stripped = line.strip()
    raw_line = line

    # Empty line
    if not stripped:
        return Token(TokenType.BLANK, "", line_number, raw_line)

    # @startuml / @enduml markers (handled separately, but just in case)
    if stripped.startswith("@startuml") or stripped.startswith("@enduml"):
        return Token(TokenType.BLANK, stripped, line_number, raw_line)

    # Abstract class definition
    abstract_class_pattern = r'^abstract\s+class\s+(\w+)\s*(\{)?'
    if re.match(abstract_class_pattern, stripped, re.IGNORECASE):
        return Token(TokenType.ABSTRACT_CLASS_START, stripped, line_number, raw_line)

    # Regular class definition
    class_pattern = r'^class\s+(\w+)\s*(\{)?'
    if re.match(class_pattern, stripped, re.IGNORECASE):
        return Token(TokenType.CLASS_START, stripped, line_number, raw_line)

    # Enum definition
    enum_pattern = r'^enum\s+(\w+)\s*\{'
    if re.match(enum_pattern, stripped, re.IGNORECASE):
        return Token(TokenType.ENUM_START, stripped, line_number, raw_line)

    # Note start
    note_pattern = r'^note\s+'
    if re.match(note_pattern, stripped, re.IGNORECASE):
        return Token(TokenType.NOTE_START, stripped, line_number, raw_line)

    # Note end
    if stripped.lower() == 'end note':
        return Token(TokenType.NOTE_END, stripped, line_number, raw_line)

    # Closing brace (class/enum end)
    if stripped == '}':
        return Token(TokenType.CLASS_END, stripped, line_number, raw_line)

    # Relationship patterns - check these before attribute pattern
    # because relationship lines can look like "A : label"
    relationship_patterns = [
        r'.*<\|--.*',      # inheritance
        r'.*--\|>.*',      # inheritance (reverse)
        r'.*\*--.*',       # composition
        r'.*--\*.*',       # composition (reverse)
        r'.*o--.*',        # aggregation
        r'.*--o.*',        # aggregation (reverse)
        r'.*-->.*',        # directed association
        r'.*<--.*',        # directed association (reverse)
        r'.*\.\..*',       # dependency
        r'^\([^)]+,[^)]+\)\s*\.\.',  # association class
        r'^\w+\s*("[^"]*")?\s*--\s*("[^"]*")?\s*\w+',  # basic association
    ]

    for pattern in relationship_patterns:
        if re.match(pattern, stripped):
            return Token(TokenType.RELATIONSHIP, stripped, line_number, raw_line)

    # Attribute pattern: name or name : Type or name : Type = default
    # Also handles const declarations
    attribute_pattern = r'^(const\s+)?(\w+)\s*(:\s*[\w\[\]<>,\s]+)?(\s*=\s*.+)?$'
    if re.match(attribute_pattern, stripped):
        return Token(TokenType.ATTRIBUTE, stripped, line_number, raw_line)

    # Enum value (simple identifier, possibly with ellipsis)
    enum_value_pattern = r'^[\w_]+$|^\.\.\.$'
    if re.match(enum_value_pattern, stripped):
        return Token(TokenType.ENUM_VALUE, stripped, line_number, raw_line)

    # If nothing matches, mark as unknown
    return Token(TokenType.UNKNOWN, stripped, line_number, raw_line)


def tokenize_block(uml_block: str) -> List[Token]:
    """
    Tokenize a complete UML block into a list of tokens.

    Args:
        uml_block: A single UML block (between @startuml and @enduml).

    Returns:
        List of Token objects in order of appearance.
    """
    # Remove comments first
    cleaned, _comments = remove_comments(uml_block)

    lines = cleaned.split('\n')
    tokens = []

    for i, line in enumerate(lines, start=1):
        token = tokenize_line(line, i)
        # Skip blank lines but keep others
        if token.type != TokenType.BLANK:
            tokens.append(token)

    return tokens


def group_multiline_constructs(tokens: List[Token]) -> List[MultiLineConstruct]:
    """
    Group tokens into multi-line constructs (classes, enums, notes).

    This is useful for parsing class bodies, enum bodies, and multi-line notes
    as single units.

    Args:
        tokens: List of tokens from tokenize_block.

    Returns:
        List of MultiLineConstruct objects.
    """
    constructs = []
    i = 0

    while i < len(tokens):
        token = tokens[i]

        # Class definition start
        if token.type in (TokenType.CLASS_START, TokenType.ABSTRACT_CLASS_START):
            is_abstract = token.type == TokenType.ABSTRACT_CLASS_START

            # Extract class name
            if is_abstract:
                match = re.match(r'abstract\s+class\s+(\w+)', token.content, re.IGNORECASE)
            else:
                match = re.match(r'class\s+(\w+)', token.content, re.IGNORECASE)

            class_name = match.group(1) if match else "Unknown"

            # Check if single-line empty class: class Name {}
            if '{}' in token.content or ('{' in token.content and '}' in token.content):
                constructs.append(MultiLineConstruct(
                    construct_type="class",
                    name=class_name,
                    is_abstract=is_abstract,
                    content_tokens=[],
                    start_line=token.line_number,
                    end_line=token.line_number
                ))
                i += 1
                continue

            # Multi-line class - gather until closing brace
            content_tokens = []
            start_line = token.line_number
            i += 1

            while i < len(tokens) and tokens[i].type != TokenType.CLASS_END:
                content_tokens.append(tokens[i])
                i += 1

            end_line = tokens[i].line_number if i < len(tokens) else start_line

            constructs.append(MultiLineConstruct(
                construct_type="class",
                name=class_name,
                is_abstract=is_abstract,
                content_tokens=content_tokens,
                start_line=start_line,
                end_line=end_line
            ))

            i += 1  # Skip the closing brace
            continue

        # Enum definition start
        if token.type == TokenType.ENUM_START:
            match = re.match(r'enum\s+(\w+)', token.content, re.IGNORECASE)
            enum_name = match.group(1) if match else "Unknown"

            # Check for inline enum: enum Name { val1, val2 }
            inline_match = re.match(r'enum\s+\w+\s*\{([^}]+)\}', token.content)
            if inline_match:
                # Parse inline values
                values_str = inline_match.group(1)
                values = [v.strip() for v in values_str.split(',') if v.strip()]

                constructs.append(MultiLineConstruct(
                    construct_type="enum",
                    name=enum_name,
                    is_abstract=False,
                    content_tokens=[Token(TokenType.ENUM_VALUE, v, token.line_number, v) for v in values],
                    start_line=token.line_number,
                    end_line=token.line_number
                ))
                i += 1
                continue

            # Multi-line enum
            content_tokens = []
            start_line = token.line_number
            i += 1

            while i < len(tokens) and tokens[i].type != TokenType.CLASS_END:
                content_tokens.append(tokens[i])
                i += 1

            end_line = tokens[i].line_number if i < len(tokens) else start_line

            constructs.append(MultiLineConstruct(
                construct_type="enum",
                name=enum_name,
                is_abstract=False,
                content_tokens=content_tokens,
                start_line=start_line,
                end_line=end_line
            ))

            i += 1  # Skip closing brace
            continue

        # Note start
        if token.type == TokenType.NOTE_START:
            content_tokens = [token]
            start_line = token.line_number
            i += 1

            while i < len(tokens) and tokens[i].type != TokenType.NOTE_END:
                content_tokens.append(tokens[i])
                i += 1

            if i < len(tokens):
                content_tokens.append(tokens[i])  # Include end note

            end_line = tokens[i].line_number if i < len(tokens) else start_line

            constructs.append(MultiLineConstruct(
                construct_type="note",
                name=None,
                is_abstract=False,
                content_tokens=content_tokens,
                start_line=start_line,
                end_line=end_line
            ))

            i += 1
            continue

        # Relationship or other standalone token - wrap as single construct
        if token.type == TokenType.RELATIONSHIP:
            constructs.append(MultiLineConstruct(
                construct_type="relationship",
                name=None,
                is_abstract=False,
                content_tokens=[token],
                start_line=token.line_number,
                end_line=token.line_number
            ))

        i += 1

    return constructs


def preprocess_uml(uml_string: str) -> Tuple[str, List[Token], List[MultiLineConstruct]]:
    """
    Complete preprocessing pipeline for a UML string.

    Args:
        uml_string: Raw PlantUML string.

    Returns:
        Tuple of (cleaned_text, tokens, grouped_constructs).
    """
    blocks = extract_uml_blocks(uml_string)
    if not blocks:
        raise ValueError("No UML blocks found")

    # For now, just process the first block
    block = blocks[0]

    tokens = tokenize_block(block)
    constructs = group_multiline_constructs(tokens)

    return block, tokens, constructs
