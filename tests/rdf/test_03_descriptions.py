"""Test 03: Description generation (schema:description)"""
import pytest
from rdflib import Graph, URIRef
from .fixtures import load_json_entity, serialize_entity

def test_q2_single_description_en():
    """Test single English description"""
    entity = load_json_entity("Q2")
    rdf_turtle = serialize_entity(entity)
    g = Graph().parse(data=rdf_turtle, format="turtle")
    
    q2_uri = URIRef("http://www.wikidata.org/entity/Q2")
    
    descriptions = list(g.objects(subject=q2_uri, predicate=URIRef("http://schema.org/description")))
    assert len(descriptions) >= 1, "Missing schema:description"
    
    en_desc = [d for d in descriptions if d.language == "en"]
    assert len(en_desc) == 1, f"Expected 1 English description"
    assert en_desc[0].value == "German city", f"Expected 'German city', got {en_desc[0].value}"

def test_q2_multi_language_descriptions():
    """Test descriptions in multiple languages"""
    entity = load_json_entity("Q2")
    rdf_turtle = serialize_entity(entity)
    g = Graph().parse(data=rdf_turtle, format="turtle")
    
    q2_uri = URIRef("http://www.wikidata.org/entity/Q2")
    
    descriptions = list(g.objects(subject=q2_uri, predicate=URIRef("http://schema.org/description")))
    desc_languages = {d.language for d in descriptions if d.language}
    
    assert "en" in desc_languages, "Missing English description"
    assert "ru" in desc_languages, "Missing Russian description"

def test_empty_descriptions():
    """Test entity with no descriptions"""
    entity = {
        "id": "Q99999",
        "type": "item",
        "descriptions": {}
    }
    rdf_turtle = serialize_entity(entity)
    g = Graph().parse(data=rdf_turtle, format="turtle")
    
    q99999_uri = URIRef("http://www.wikidata.org/entity/Q99999")
    descriptions = list(g.objects(subject=q99999_uri, predicate=URIRef("http://schema.org/description")))
    assert len(descriptions) == 0, "Expected 0 descriptions"
