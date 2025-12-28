"""Test 04: Alias generation (skos:altLabel)"""
import pytest
from rdflib import Graph, URIRef
from .fixtures import load_json_entity, serialize_entity

def test_q2_aliases_en():
    """Test aliases in English"""
    entity = load_json_entity("Q2")
    rdf_turtle = serialize_entity(entity)
    g = Graph().parse(data=rdf_turtle, format="turtle")
    
    q2_uri = URIRef("http://www.wikidata.org/entity/Q2")
    
    aliases = list(g.objects(subject=q2_uri, predicate=URIRef("http://www.w3.org/2004/02/skos/core#altLabel")))
    en_aliases = [a for a in aliases if a.language == "en"]
    
    assert len(en_aliases) == 2, f"Expected 2 English aliases, got {len(en_aliases)}"
    alias_values = {a.value for a in en_aliases}
    assert "Berlin, Germany" in alias_values, "Missing 'Berlin, Germany' alias"
    assert "Land Berlin" in alias_values, "Missing 'Land Berlin' alias"

def test_q2_aliases_multi_language():
    """Test aliases in multiple languages"""
    entity = load_json_entity("Q2")
    rdf_turtle = serialize_entity(entity)
    g = Graph().parse(data=rdf_turtle, format="turtle")
    
    q2_uri = URIRef("http://www.wikidata.org/entity/Q2")
    
    aliases = list(g.objects(subject=q2_uri, predicate=URIRef("http://www.w3.org/2004/02/skos/core#altLabel")))
    alias_languages = {a.language for a in aliases if a.language}
    
    assert "en" in alias_languages, "Missing English aliases"
    assert "ru" in alias_languages, "Missing Russian aliases"
    
    ru_aliases = [a for a in aliases if a.language == "ru"]
    assert len(ru_aliases) == 1, f"Expected 1 Russian alias, got {len(ru_aliases)}"
    assert ru_aliases[0].value == "Берлин", f"Expected 'Берлин', got {ru_aliases[0].value}"

def test_empty_aliases():
    """Test entity with no aliases"""
    entity = {
        "id": "Q99999",
        "type": "item",
        "aliases": {}
    }
    rdf_turtle = serialize_entity(entity)
    g = Graph().parse(data=rdf_turtle, format="turtle")
    
    q99999_uri = URIRef("http://www.wikidata.org/entity/Q99999")
    aliases = list(g.objects(subject=q99999_uri, predicate=URIRef("http://www.w3.org/2004/02/skos/core#altLabel")))
    assert len(aliases) == 0, "Expected 0 aliases"
