import re
import networkx as nx
import difflib
import nltk
from nltk.stem import WordNetLemmatizer

# Download required NLTK data files (run these lines once)
nltk.download('wordnet')
nltk.download('omw-1.4')

def extract_uml_blocks(input_text):
    """
    Extracts all UML blocks from the input text.
    A UML block is defined as text starting with '@startuml' and ending with '@enduml'.
    
    Parameters:
        input_text (str): The raw input containing one or more UML blocks.
    
    Returns:
        List[str]: A list of UML block strings (including the start and end markers).
    """
    pattern = r"@startuml(.*?)@enduml"
    matches = re.findall(pattern, input_text, flags=re.DOTALL)
    blocks = [f"@startuml{match}@enduml" for match in matches]
    return blocks

def check_for_explicit_class_definitions(block):
    """
    Checks if the UML block contains explicit class definitions, which are not allowed.
    
    Parameters:
        block (str): The UML block string.
    
    Raises:
        ValueError: If an explicit class definition is found.
    
    Returns:
        True if no explicit definitions are found.
    """
    pattern = r'^\s*(class|interface)\s+\w+'
    if re.search(pattern, block, flags=re.MULTILINE):
        raise ValueError("Explicit class definitions are not allowed. Use implicit definitions via relationships.")
    return True

def validate_uml_block(block):
    """
    Validates a single UML block for correct start/end markers and content.
    
    Parameters:
        block (str): A single UML block string.
    
    Raises:
        ValueError: If validation fails.
    
    Returns:
        True if the block is valid.
    """
    lines = [line.strip() for line in block.strip().splitlines() if line.strip()]
    if not lines:
        raise ValueError("UML block is empty.")
    if lines[0] != "@startuml":
        raise ValueError("UML block does not start with '@startuml'.")
    if lines[-1] != "@enduml":
        raise ValueError("UML block does not end with '@enduml'.")
    if len(lines) < 3:
        raise ValueError("UML block does not contain any diagram content.")
    check_for_explicit_class_definitions(block)
    return True

def validate_uml_input(input_text):
    """
    Validates the entire UML input, ensuring no extraneous content outside blocks.
    
    Parameters:
        input_text (str): The full UML input.
    
    Raises:
        ValueError: If validation fails.
    
    Returns:
        True if the input is valid.
    """
    if not isinstance(input_text, str):
        raise ValueError("Input must be a string.")
    matches = list(re.finditer(r"@startuml.*?@enduml", input_text, flags=re.DOTALL))
    if not matches:
        raise ValueError("No UML blocks found in the input.")
    last_end = 0
    for m in matches:
        if input_text[last_end:m.start()].strip():
            raise ValueError("Extraneous content found outside UML blocks.")
        last_end = m.end()
    if input_text[last_end:].strip():
        raise ValueError("Extraneous content found outside UML blocks.")
    for m in matches:
        validate_uml_block(m.group(0))
    return True

# Define identifier pattern for class names and attributes
identifier_pattern = r"[A-Za-z0-9_&]+"

# Line parsing functions
def parse_attribute_line(line):
    """Parses a line like 'ClassName : attributeName'."""
    pattern = rf'^\s*({identifier_pattern})\s*:\s*({identifier_pattern})\s*$'
    match = re.match(pattern, line)
    return (match.group(1), match.group(2)) if match else None

def parse_association_line(line):
    """Parses a line like 'Class1 "card" -- "card" Class2 [: label]'."""
    pattern = (
        rf'^({identifier_pattern})\s*'
        r'("[0-9\.\.\*]+"|"\*")?\s*'
        r'(?<![o*])--(?![o*])\s*'
        r'("[0-9\.\.\*]+"|"\*")?\s*'
        rf'({identifier_pattern})'
        r'(?:\s*:\s*([^\n]+))?$'
    )
    match = re.match(pattern, line)
    if match:
        class_1 = match.group(1)
        kard1 = match.group(2).strip('"') if match.group(2) else None
        kard2 = match.group(3).strip('"') if match.group(3) else None
        class_2 = match.group(4)
        label = match.group(5).strip() if match.group(5) else ''
        return (class_1, kard1, kard2, class_2, label)
    return None

def parse_generalization_line(line):
    """Parses a line like 'Class1 <|-- Class2' or 'Class1 --|> Class2'."""
    pattern = rf'^({identifier_pattern})\s*(<\|--|--\|>)\s*({identifier_pattern})$'
    match = re.match(pattern, line)
    if match:
        class1, arrow, class2 = match.group(1), match.group(2), match.group(3)
        parent = class1 if arrow == '<|--' else class2
        child = class2 if arrow == '<|--' else class1
        return (parent, child)
    return None

def parse_aggregation_line(line):
    """Parses a line like 'ClassA "1" o-- "1..*" ClassB'."""
    pattern = (
        rf'^({identifier_pattern})'
        r'\s*("[0-9\.\.\*]+"|"\*")?'
        r'\s*(o--|--o)\s*'
        r'("[0-9\.\.\*]+"|"\*")?'
        rf'\s*({identifier_pattern})$'
    )
    match = re.match(pattern, line)
    if match:
        class_1 = match.group(1)
        kard1 = match.group(2).strip('"') if match.group(2) else None
        arrow = match.group(3)
        kard2 = match.group(4).strip('"') if match.group(4) else None
        class_2 = match.group(5)
        aggregator, aggregated = (class_1, class_2) if arrow == 'o--' else (class_2, class_1)
        aggregator_kard, aggregated_kard = (kard1, kard2) if arrow == 'o--' else (kard2, kard1)
        return (aggregator, aggregator_kard, aggregated, aggregated_kard)
    return None

def parse_composition_line(line):
    """Parses a line like 'ClassA "1" *-- "1..*" ClassB'."""
    pattern = (
        rf'^({identifier_pattern})'
        r'\s*("[0-9\.\.\*]+"|"\*")?'
        r'\s*(\*--|--\*)\s*'
        r'("[0-9\.\.\*]+"|"\*")?'
        rf'\s*({identifier_pattern})$'
    )
    match = re.match(pattern, line)
    if match:
        class_1 = match.group(1)
        kard1 = match.group(2).strip('"') if match.group(2) else None
        arrow = match.group(3)
        kard2 = match.group(4).strip('"') if match.group(4) else None
        class_2 = match.group(5)
        composite, part = (class_1, class_2) if arrow == '*--' else (class_2, class_1)
        composite_kard, part_kard = (kard1, kard2) if arrow == '*--' else (kard2, kard1)
        return (composite, composite_kard, part, part_kard)
    return None

def parse_uml_string(uml_string):
    """
    Parses a UML string line by line into structured data.
    
    Returns:
        dict: Contains 'classes', 'attributes', 'associations', 'generalizations',
              'aggregations', 'compositions'.
    """
    lines = [line.strip() for line in uml_string.strip().splitlines() if line.strip()]
    if not lines or lines[0] != "@startuml" or lines[-1] != "@enduml":
        raise ValueError("UML string must start with '@startuml' and end with '@enduml'.")
    content_lines = lines[1:-1]
    if not content_lines:
        raise ValueError("No UML content between '@startuml' and '@enduml'.")
    
    parsed_info = {
        'attributes': [],
        'associations': [],
        'generalizations': [],
        'aggregations': [],
        'compositions': [],
    }
    
    parsers = [
        (parse_attribute_line, 'attributes'),
        (parse_association_line, 'associations'),
        (parse_generalization_line, 'generalizations'),
        (parse_aggregation_line, 'aggregations'),
        (parse_composition_line, 'compositions'),
    ]
    
    for line in content_lines:
        parsed = False
        for parse_func, key in parsers:
            result = parse_func(line)
            if result:
                parsed_info[key].append(result)
                parsed = True
                break
        if not parsed:
            raise ValueError(f"Unrecognized UML line: '{line}'")
    
    classes_set = set()
    for cls, _ in parsed_info['attributes']:
        classes_set.add(cls)
    for cls1, _, _, cls2, _ in parsed_info['associations']:
        classes_set.add(cls1)
        classes_set.add(cls2)
    for parent, child in parsed_info['generalizations']:
        classes_set.add(parent)
        classes_set.add(child)
    for agg, _, aggd, _ in parsed_info['aggregations']:
        classes_set.add(agg)
        classes_set.add(aggd)
    for comp, _, part, _ in parsed_info['compositions']:
        classes_set.add(comp)
        classes_set.add(part)
    parsed_info['classes'] = sorted(classes_set)
    
    return parsed_info

# Remaining functions (assumed unchanged)
def normalize_name(name):
    lemmatizer = WordNetLemmatizer()
    return ''.join(lemmatizer.lemmatize(word.lower()) for word in re.findall(r'\w+', name))

def edge_signature_normalized(edge_data):
    return (
        edge_data['type'],
        edge_data.get('kard1', ''),
        edge_data.get('kard2', ''),
        normalize_name(edge_data.get('label', ''))
    )

def parsed_info_to_graph(parsed_info):
    G = nx.DiGraph()
    for cls in parsed_info['classes']:
        G.add_node(cls, attributes=[attr for c, attr in parsed_info['attributes'] if c == cls])
    for parent, child in parsed_info['generalizations']:
        G.add_edge(parent, child, type='generalization')
    for class1, kard1, kard2, class2, label in parsed_info['associations']:
        G.add_edge(class1, class2, type='association', kard1=kard1, kard2=kard2, label=label)
        G.add_edge(class2, class1, type='association', kard1=kard2, kard2=kard1, label=label)
    for agg, agg_kard, aggd, aggd_kard in parsed_info['aggregations']:
        G.add_edge(agg, aggd, type='aggregation', kard1=agg_kard, kard2=aggd_kard)
    for comp, comp_kard, part, part_kard in parsed_info['compositions']:
        G.add_edge(comp, part, type='composition', kard1=comp_kard, kard2=part_kard)
    return G







