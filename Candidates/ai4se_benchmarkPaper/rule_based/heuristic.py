
import spacy
from spacy import displacy
import re
import os

import random
import string


# Load spaCy model
nlp = spacy.load("en_core_web_sm")


def clean_text(text):
    
    # Remove unknown symbols or non-printable characters
    text = re.sub(r'[^\x00-\x7F]+', '', text)  # Keeps only ASCII characters
    
    # Remove specified symbols (*, +, and parentheses)
    text = re.sub(r'[()*+]', '', text)  # Remove *, +, (, and )
    
    # Space around periods
    rem_space = re.sub(r'\.\s+', ' . ', text)
    
    return rem_space

###################################
# Class Extraction
##################################

#Extract common nouns (NN) and proper nouns (NNP) and map them to classes
def c_rule_extract_classes(doc):
    classes =[] 
    for token in doc:
        if token.pos_ in {'NOUN','PROPN'}: # Nouns and Proper noun  'NN', 'NNP'
            classes.append(token.text)
    return classes

# Map Subject  and Object  forms to candidate classes based on verb 
def c_rule_extract_svo(doc, candidate_classes):
    # Iterate through tokens to find verbs and associated subjects/objects
    for token in doc:
        if token.pos_ == "VERB":  # Identify a verb
            
            # Initialize placeholders for subject and object
            subject = None
            obj = None

            # Find associated subject and object for the verb
            for child in token.children:
                if child.dep_ in {"nsubj"} and child.pos_ in {"NOUN", "PROPN"} and child.text not in candidate_classes: 
                    subject = child.text
                elif child.dep_ in {"dobj"} and child.pos_ in {"NOUN", "PROPN"} and child.text not in candidate_classes: 
                    obj = child.text
            
            # If both subject and object are found, add them to candidate classes and print the extracted pair
            if subject and obj:
                candidate_classes.append(subject)
                candidate_classes.append(obj)
                #print(f"Extracted Subject: {subject}, Object: {obj}")

    return candidate_classes

###################################
# Relationship Extraction
###################################

association_verbs = {
    "take", "send", "buy", "give", "show", "record", "work", "talk"
}

def extract_relationships_association(doc, fin_cls, verbs_phrase, relationship_type):
    """
    Extracts association relationships. 
    """
    relationships = []
    fin_cls_lower = set(c.lower() for c in fin_cls)

    for token in doc:
        # Check if the token is a verb and in the specified verb list
        if token.pos_ == "VERB" and token.lemma_ in verbs_phrase:
            verb_nm = token.text
            subjects = set()
            objects = set()

            # Identify subjects for the relationship
            for child in token.children:
                if child.dep_ in {"nsubj"} and child.text.lower() in fin_cls_lower: 
                    subjects.add(child.text)  # Capture subject
                    # Handle conjunctive subjects
                    for conj in child.children:
                        if conj.dep_ == "conj" and conj.text.lower() in fin_cls_lower:
                            subjects.add(conj.text)

            # Identify direct objects (dobj) for the relationship
            for child in token.children:
                if child.dep_ == "dobj" and child.text.lower() in fin_cls_lower:
                    objects.add(child.text)  # Capture object
                    # Handle conjunctive direct objects
                    for conj in child.children:
                        if conj.dep_ == "conj" and conj.text.lower() in fin_cls_lower:
                            objects.add(conj.text)  # Capture object

            # Identify prepositional objects (prep + pobj) for the relationship
            verb_phrase = verb_nm  # extracted verb phrase is the verb
            for child in token.children:
                if child.dep_ == "prep" and child.pos_ == "ADP":
                    prep = child.text  # Capture the preposition to include with the verb
                    for pobj in child.children:
                        if pobj.dep_ == "pobj" and pobj.text.lower() in fin_cls_lower:
                            objects.add(pobj.text)  # Capture prepositional object
                            # Handle conjunctive prepositional objects
                            for conj in pobj.children:
                                if conj.dep_ == "conj" and conj.text.lower() in fin_cls_lower:
                                    objects.add(conj.text)  # Capture object
                    # Append the preposition to the verb to form a verb phrase
                    verb_phrase = f"{verb_nm} {prep}"

            # Handle conjunctive verbs and their objects
            for conj in token.children:
                if conj.dep_ == "conj" and conj.pos_ == "VERB" and conj.lemma_ in verbs_phrase:
                    conj_verb_nm = conj.text
                    conj_objects = set()
                    conj_verb_phrase = conj_verb_nm  # Default to verb only for the conjunctive verb
                    # Identify objects for the conjunctive verb
                    for child in conj.children:
                        if child.dep_ == "dobj" and child.text.lower() in fin_cls_lower:
                            conj_objects.add(child.text)  # Capture object
                            # Handle conjunctive direct objects for the conjunctive verb
                            for conj_obj in child.children:
                                if conj_obj.dep_ == "conj" and conj_obj.text.lower() in fin_cls_lower:
                                    conj_objects.add(conj_obj.text)  # Capture object
                        elif child.dep_ == "prep" and child.pos_ == "ADP":
                            conj_prep = child.text  # Capture the preposition
                            for pobj in child.children:
                                if pobj.dep_ == "pobj" and pobj.text.lower() in fin_cls_lower:
                                    conj_objects.add(pobj.text)  # Capture prepositional object
                                    # Handle conjunctive prepositional objects
                                    for conj_pobj in pobj.children:
                                        if conj_pobj.dep_ == "conj" and conj_pobj.text.lower() in fin_cls_lower:
                                            conj_objects.add(conj_pobj.text)  # Capture object
                            # Form the verb phrase with preposition
                            conj_verb_phrase = f"{conj_verb_nm} {conj_prep}"

                    # Store relationships for the conjunctive verb with verb phrase
                    for subject in subjects:
                        for obj in conj_objects:
                            # Capitalize subject/object
                            cap_subj = subj.capitalize()
                            cap_obj = obj.capitalize()
                            relationship_tuple = (cap_subj, conj_verb_phrase, cap_obj)
                            relationships.append((relationship_type, relationship_tuple))
                            #print(f"Extracted {relationship_type} - {relationship_tuple}")

            # Create individual tuples for the primary verb and each subject-object pair
            for subj in subjects:
                for obj in objects:
                    cap_subj = subj.capitalize()
                    cap_obj = obj.capitalize()
                    relationship_tuple = (cap_subj, verb_phrase, cap_obj)
                    relationships.append((relationship_type, relationship_tuple))
                    #print(f"Extracted {relationship_type} - {relationship_tuple}")

    return relationships



aggregation_verbs = {
    "hold", "carry", "involve", "imply", "embrace",
    "consist", "comprise", "belong", "divide", "include"
}

def extract_relationships_aggregation(doc, fin_cls, verbs_phrase, relationship_type):
    """
    Extracts aggregation relationships. 
    """
    relationships = []
    fin_cls_lower = set(c.lower() for c in fin_cls)

    for token in doc:
        # Check if the token is a verb in the specified verb list
        if token.pos_ == "VERB" and token.lemma_ in verbs_phrase:
            verb_lemma = token.lemma_
            subjects = set()
            objects = set()
            verb_phrase = verb_lemma # Default to just the verb

            # Identify subjects for the relationship
            for child in token.children:
                if child.dep_ in {"nsubj"} and child.text.lower() in fin_cls_lower:
                    subjects.add(child.text)
                    # Handle conjunctive subjects
                    for conj in child.children:
                        if conj.dep_ == "conj" and conj.text.lower() in fin_cls_lower:
                            subjects.add(conj.text)

            # Identify direct objects (dobj)
            for child in token.children:
                if child.dep_ == "dobj" and child.text.lower() in fin_cls_lower:
                    objects.add(child.text)
                    # Handle conjunctive direct objects
                    for conj in child.children:
                        if conj.dep_ == "conj" and conj.text.lower() in fin_cls_lower:
                            objects.add(conj.text)

            # Handle prepositions if needed
            #  - "consist"/"comprise" → only "of"
            #  - "belong"/"divide"   → only "to"
            #  - "include" →  only "in"
            #  - otherwise, skip any prepositional objects
            for child in token.children:
                if child.dep_ == "prep" and child.pos_ == "ADP":
                    prep = child.text.lower()

                    # Decide if we handle this preposition
                    if verb_lemma in {"consist", "comprise"}:
                        # Must be "of" to accept
                        if prep != "of":
                            continue
                    elif verb_lemma in {"belong", "divide"}:
                        # Must be "to" to accept
                        if prep != "to":
                            continue
                    elif verb_lemma == "include":
                        # Must be "in" to accept
                        if prep != "in":
                            continue
                    else:
                        # For all other aggregator verbs, skip any preposition
                        continue

                    # If we get here, we accept this preposition
                    for pobj in child.children:
                        if pobj.dep_ == "pobj" and pobj.text.lower() in fin_cls_lower:
                            objects.add(pobj.text)
                            # Handle conjunctive pobj
                            for conj in pobj.children:
                                if conj.dep_ == "conj" and conj.text.lower() in fin_cls_lower:
                                   objects.add(conj.text)
                    # Append the accepted preposition to the verb phrase
                    verb_phrase = f"{verb_lemma} {prep}"

            # Handle conjunctive verbs
            for conj in token.children:
                if conj.dep_ == "conj" and conj.pos_ == "VERB" and conj.lemma_ in verbs_phrase:
                    conj_verb_lemma = conj.lemma_
                    conj_verb_phrase = conj_verb_lemma
                    conj_objects = set()

                    for child2 in conj.children:
                        if child2.dep_ == "dobj" and child2.text.lower() in fin_cls_lower:
                            conj_objects.add(child2.text)
                            # Handle conjunctive direct objects
                            for conj_obj in child2.children:
                                if conj_obj.dep_ == "conj" and conj_obj.text.lower() in fin_cls_lower:
                                    conj_objects.add(conj_obj.text)
                        elif child2.dep_ == "prep" and child2.pos_ == "ADP":
                            conj_prep = child2.text.lower()

                            if conj_verb_lemma in {"consist", "comprise"}:
                                if conj_prep != "of":
                                    continue
                            elif conj_verb_lemma in {"belong", "divide"}:
                                if conj_prep != "to":
                                    continue
                            elif conj_verb_lemma == "include":
                                # Must be "in" to accept
                                if prep != "in":
                                    continue
                            else:
                                continue

                            for pobj2 in child2.children:
                                if pobj2.dep_ == "pobj" and pobj2.text.lower() in fin_cls_lower:
                                    conj_objects.add(pobj2.text)
                                    for conj_pobj in pobj2.children:
                                        if conj_pobj.dep_ == "conj" and conj_pobj.text.lower() in fin_cls_lower:
                                            #conj_objects.add(get_compound_phrase(conj_pobj))
                                            conj_objects.add(conj_pobj.text)
                            conj_verb_phrase = f"{conj_verb_lemma} {conj_prep}"

                    # Store relationships for the conjunctive verb
                    for subj in subjects:
                        for obj in conj_objects:
                            cap_subj = subj.capitalize()
                            cap_obj = obj.capitalize()
                            relationship_tuple = (cap_subj, conj_verb_phrase, cap_obj)
                            relationships.append((relationship_type, relationship_tuple))

            # Finally, create individual tuples for the main verb
            for subj in subjects:
                for obj in objects:
                    cap_subj = subj.capitalize()
                    cap_obj = obj.capitalize()
                    relationship_tuple = (cap_subj, verb_phrase, cap_obj)
                    relationships.append((relationship_type, relationship_tuple))

    return relationships



composition_verbs = {
    "have", "comprise", "possess", "contain"
}

def extract_relationships_composition(doc, fin_cls, verbs_phrase, relationship_type):
    """
    Extracts composition relationships by ignoring prepositional objects 
    """
    relationships = []
    fin_cls_lower = {c.lower() for c in fin_cls}

    for token in doc:
        # Check if the token is a verb in the composition_verbs set
        if token.pos_ == "VERB" and token.lemma_ in verbs_phrase:
            verb_lemma = token.lemma_
            subjects = set()
            objects = set()
            verb_phrase = verb_lemma  # By default, just the lemma

            # Identify subjects (nsubj)
            for child in token.children:
                if child.dep_ in {"nsubj"} and child.text.lower() in fin_cls_lower: 
                    subjects.add(child.text)
                    # Handle conjunctive subjects
                    for conj in child.children:
                        if conj.dep_ == "conj" and conj.text.lower() in fin_cls_lower:
                            subjects.add(conj.text)

            # Identify direct objects (dobj)
            for child in token.children:
                if child.dep_ == "dobj" and child.text.lower() in fin_cls_lower:
                    objects.add(child.text)
                    # Handle conjunctive direct objects
                    for conj in child.children:
                        if conj.dep_ == "conj" and conj.text.lower() in fin_cls_lower:
                            objects.add(conj.text)

            # Skip any prepositional objects for composition
            # If you want to entirely ignore them, do not parse them.
            # (Commented out logic that used to handle child.dep_ == "prep")
            #
            # for child in token.children:
            #     if child.dep_ == "prep" and child.pos_ == "ADP":
            #         # For composition, we skip
            #         pass

            # Handle conjunctive verbs
            for conj in token.children:
                if conj.dep_ == "conj" and conj.pos_ == "VERB" and conj.lemma_ in verbs_phrase:
                    conj_verb_lemma = conj.lemma_
                    conj_verb_phrase = conj_verb_lemma
                    conj_objects = set()

                    for child2 in conj.children:
                        if child2.dep_ == "dobj" and child2.text.lower() in fin_cls_lower:
                            conj_objects.add(child2.text)
                            # Handle conjunctive direct objects
                            for conj_obj in child2.children:
                                if conj_obj.dep_ == "conj" and conj_obj.text.lower() in fin_cls_lower:
                                    conj_objects.add(conj_obj.text)
                        # Skip any prepositional children for composition

                    # Store relationships for the conjunctive verb
                    for subj in subjects:
                        for obj in conj_objects:
                            cap_subj = subj.capitalize()
                            cap_obj = obj.capitalize()
                            # Reverse the direction: object -> subject
                            relationship_tuple = (cap_obj, conj_verb_phrase, cap_subj)
                            relationships.append((relationship_type, relationship_tuple))

            # Finally, create individual tuples for the main verb
            for subj in subjects:
                for obj in objects:
                    cap_subj = subj.capitalize()
                    cap_obj = obj.capitalize()
                    # Reverse direction: object -> subject
                    relationship_tuple = (cap_obj, verb_phrase, cap_subj)
                    relationships.append((relationship_type, relationship_tuple))

    return relationships



def extract_include_relationship(doc, fin_cls):
    """
    Extracts composition relationship for "include" phrase separately
    """
    relationships = []
    fin_cls_lower = set(c.lower() for c in fin_cls)

    for token in doc:
        # Check if the lemma of the token is "include"
        if token.lemma_ == "include" and token.pos_ == "VERB":
            subject = None
            objects = set()

            # Step 1: Identify the subject (nsubj or noun before "include")
            for child in token.children:
                if child.dep_ in {"nsubj"} and child.text.lower() in fin_cls_lower: 
                    subject = child.text
                    break
            
            # Step 2: Identify the objects (dobj following "include")
            for child in token.children:
                if child.dep_ in {"dobj"} and child.text.lower() in fin_cls_lower:
                    # Capture main object
                    obj = child.text
                    objects.add(obj)
                    
                    # Handle conjunctive objects 
                    for conj in child.children:
                        if conj.dep_ == "conj" and conj.text.lower() in fin_cls_lower:
                            conj_obj = conj.text
                            objects.add(conj_obj)

            # Step 3: Store the relationship if both subject and objects are identified and not identical
            if subject:
                for obj in objects:
                    if subject != obj:  # Discard if subject and object are the same
                        cap_subj = subject.capitalize()
                        cap_obj = obj.capitalize()
                        relationship_tuple = (cap_obj, "include", cap_subj)
                        relationships.append(relationship_tuple)
                        #print(f"Extracted Include Relationship - {relationship_tuple}")

    return relationships


def extract_generalization(doc, fin_cls):
    """
    Extracts generalization relationships with selected verb phrases and copulas.
    """
    relationships = []
    fin_cls_lower = {c.lower() for c in fin_cls}
    # Reserved words that appear in key phrases and should not be selected as candidate classes.
    reserved_words = {"category", "type", "kind", "a"}
    
    processed = False  # Indicates if we processed a copular construction in the sentence.

    for sent in doc.sents:
        for token in sent:
            if token.lemma_ == "be":
                processed = True
                subj = None
                obj = None
                reverse = False  # Flag to reverse the relationship direction

                # Check for cues "maybe" or auxiliary "can"
                for child in token.children:
                    if child.text.lower() == "maybe":
                        reverse = True
                        break
                    if child.lemma_ == "can" and child.dep_ == "aux":
                        reverse = True
                        break

                # Find subject: look among children for nsubj that is in fin_cls and not reserved.
                for child in token.children:
                    if (child.dep_ in {"nsubj"}   
                        and child.text.lower() in fin_cls_lower 
                        and child.text.lower() not in reserved_words):
                        #subj = get_compound_phrase(child)
                        subj = child.text
                        break

                # Find object: try to get an attribute (attr or acomp) first.
                for child in token.children:
                    if (child.dep_ in {"attr", "acomp"} 
                        and child.text.lower() in fin_cls_lower 
                        and child.text.lower() not in reserved_words):
                        obj = child.text
                        break

                # If no attribute found, look for a prepositional phrase with "of".
                if not obj:
                    for child in token.children:
                        if child.dep_ == "prep" and child.text.lower() == "of":
                            for pobj in child.children:
                                if (pobj.dep_ == "pobj" 
                                    and pobj.text.lower() in fin_cls_lower
                                    and pobj.text.lower() not in reserved_words):
                                    #obj = get_compound_phrase(pobj)
                                    obj = pobj.text
                                    break
                            if obj:
                                break

                # If we found both subject and object
                if subj and obj:
                    cap_subj = subj.capitalize()
                    cap_obj = obj.capitalize()
                    if reverse:
                        relationships.append((cap_obj, cap_subj))
                    else:
                        relationships.append((cap_subj, cap_obj))
                break  # Only process the first copular construction in the sentence

        # Fallback: if no copular verb was processed and "maybe" is present in the sentence.
        if not processed and "maybe" in sent.text.lower():
            tokens = list(sent)
            subj = None
            obj = None
            maybe_index = None
            for i, t in enumerate(tokens):
                if t.text.lower() == "maybe":
                    maybe_index = t.idx
                    break
            if maybe_index is not None:
                # Look backwards for the last candidate class before "maybe" (ignoring reserved words)
                for t in reversed(tokens):
                    if (t.idx < maybe_index 
                        and t.text.lower() in fin_cls_lower
                        and t.text.lower() not in reserved_words):
                        #subj = get_compound_phrase(t)
                        subj = t.text
                        break
                # Look forwards for the first candidate class after "maybe"
                for t in tokens:
                    if (t.idx > maybe_index 
                        and t.text.lower() in fin_cls_lower
                        and t.text.lower() not in reserved_words):
                        obj = t.text
                        break
                if subj and obj:
                    cap_subj = subj.capitalize()
                    cap_obj = obj.capitalize()
                    relationships.append((cap_obj, cap_subj))
        processed = False

    return relationships

##########################################
# Mapping and handling Plantuml generation 
##########################################

# Create a dictionary to map CamelCased terms to their original forms
def create_original_term_map(candidate_classes):
    term_map = {}
    for term in candidate_classes:
        camel_cased = ''.join(word.capitalize() for word in term.split())
        term_map[camel_cased] = term
    return term_map

def get_cardinality(term, original_term_map):
    """Helper function to determine cardinality based on the original term."""
    original_term = original_term_map.get(term, term).lower()  # Use original term or fallback to term
    doc = nlp(original_term)
    for token in doc:
        if token.tag_ in {"NNS", "NNPS"}:  # Plural
            return "1..*"
    return "1"  # Default to singular

def add_relationships(relationships, symbol, get_cardinality):
    """Helper function to add relationships with cardinalities."""
    content = ""
    for relationship in relationships:
        if len(relationship) == 2 and symbol == "<|--":  # Generalization relationships
            subject, obj = relationship
            content += f"{subject} <|-- {obj} \n"
        elif len(relationship) == 3 and symbol == "*--":  # Include relationships using composition symbol
            subject, relation, obj = relationship
            # Determine cardinalities using original terms
            subject_card = get_cardinality(subject)
            obj_card = get_cardinality(obj)
            content += f"{subject} \"{subject_card}\" *-- \"{obj_card}\" {obj}\n"
        elif len(relationship) == 2:
            # e.g. (relationship_type, (subject, verb_phrase, object))
            relationship_type, (subject, verb_phrase, obj) = relationship
            subj_card = get_cardinality(subject)
            obj_card = get_cardinality(obj)

            if symbol == "--":
                # Association => show label
                content += f"{subject} \"{subj_card}\" -- \"{obj_card}\" {obj} : {verb_phrase}\n"
            elif symbol in {"o--", "*--"}:
                # Aggregation or normal composition => no label
                content += f"{subject} \"{subj_card}\" {symbol} \"{obj_card}\" {obj}\n"
    return content



def _random_name(length=8):
    """Generate a random gibberish class name of a given length."""
    # Use lowercase letters, then capitalize the result
    letters = string.ascii_lowercase
    name = ''.join(random.choice(letters) for _ in range(length))
    return name.capitalize()

def generate_plantuml(doc, final_candidate_classes):
    """
    Generate PlantUML content based on relationships extracted from the document.
    Ensures we never produce an empty diagram by inserting a fallback line with random names
    if no classes and no relationships are found.
    """
    # Map CamelCased terms to their original forms for cardinality checks
    original_term_map = create_original_term_map(final_candidate_classes)

    # Extract relationships using the provided functions
    association_relationships = extract_relationships_association(
        doc, final_candidate_classes, association_verbs, "Association"
    )
    aggregation_relationships = extract_relationships_aggregation(
        doc, final_candidate_classes, aggregation_verbs, "Aggregation"
    )
    composition_relationships = extract_relationships_composition(
        doc, final_candidate_classes, composition_verbs, "Composition"
    )
    include_relationships = extract_include_relationship(doc, final_candidate_classes)
    generalization_relationships = extract_generalization(doc, final_candidate_classes)

    # Check if we have any relationships at all
    has_relationships = any([
        association_relationships,
        aggregation_relationships,
        composition_relationships,
        include_relationships,
        generalization_relationships
    ])

    plantuml_content = "@startuml\n\n"

    if has_relationships:
        # Normal path: add whatever relationships we found
        plantuml_content += add_relationships(
            association_relationships, "--", lambda term: get_cardinality(term, original_term_map)
        )
        plantuml_content += add_relationships(
            aggregation_relationships, "o--", lambda term: get_cardinality(term, original_term_map)
        )
        plantuml_content += add_relationships(
            composition_relationships, "*--", lambda term: get_cardinality(term, original_term_map)
        )
        plantuml_content += add_relationships(
            include_relationships, "*--", lambda term: get_cardinality(term, original_term_map)
        )
        plantuml_content += add_relationships(
            generalization_relationships, "<|--", lambda term: get_cardinality(term, original_term_map)
        )
    else:
        # No classes and no relationships => produce random class name with association relation
        random_class_1 = _random_name()
        random_class_2 = _random_name()
        plantuml_content += f"{random_class_1} -- {random_class_2}\n"

    plantuml_content += "\n@enduml\n"
    return plantuml_content


def generate_uml_from_text(scenario_text):
    """
    Generate UML directly from an in-memory string `scenario_text`
    and return the UML content as a string.
    """
    # 1) Clean and process the text
    cleaned = clean_text(scenario_text)
    doc = nlp(cleaned)

    # 2) Extract classes
    candidate_classes = c_rule_extract_classes(doc)
    final_candidate_classes = c_rule_extract_svo(doc, candidate_classes)

    # 3) Generate PlantUML content
    uml_content = generate_plantuml(doc, final_candidate_classes)
    return uml_content


def generate_uml_from_text_file(input_file_path, output_file_path):
    """
    Generate UML from a text file and save the output to a file.
    """
    # Read input text file in binary mode to handle non-UTF-8 characters
    with open(input_file_path, 'rb') as file:
        binary_content = file.read()

    # Decode content with 'utf-8' while ignoring errors
    text = binary_content.decode('utf-8', errors='ignore')

    # Optionally, remove BOM if present
    if text.startswith('\ufeff'):
        text = text[1:]

    # Reuse the new function
    uml_content = generate_uml_from_text(text)

    # Write UML content to the output file
    with open(output_file_path, 'w', encoding='utf-8') as file:
        file.write(uml_content)
