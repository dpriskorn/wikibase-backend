"""Test 09: Monolingual text values (text + language tag)"""
import pytest
from rdflib import Graph, URIRef, Literal
from .fixtures import load_json_entity, serialize_entity

def test_value_monolingualtext():
    """Test monolingualtext datatype produces language-tagged literal"""
    entity = load_json_entity("Q4")
    rdf_turtle = serialize_entity(entity)
    g = Graph().parse(data=rdf_turtle, format="turtle")
    
    # Find P5 statement (monolingualtext type)
    stmt = [s for s in g.subjects() if "TEST-Statement-5-93da31338cb80c2eb0f92a5459186bd59579180" in str(s)][0]
    
    value = list(g.objects(subject=stmt, predicate=URIRef("http://www.wikidata.org/prop/statement/P5")))[0]
    
    assert isinstance(value, Literal), f"Expected Literal for monolingualtext"
    assert value.language == "ru", f"Expected language 'ru', got {value.language}"
    assert "превед" in value.value, f"Expected 'превед' in value, got {value.value}"

def test_monolingualtext_different_values():
    """Test different monolingualtext values have different values"""
    entity = load_json_entity("Q4")
    rdf_turtle = serialize_entity(entity)
    g = Graph().parse(data=rdf_turtle, format="turtle")
    
    q4_uri = URIRef("http://www.wikidata.org/entity/Q4")
    
    # Get all P5 direct values
    p5_values = list(g.objects(subject=q4_uri, predicate=URIRef("http://www.wikidata.org/prop/direct/P5")))
    
    assert len(p5_values) == 2, f"Expected 2 monolingualtext values for P5"
    
    value_set = {v.value for v in p5_values if isinstance(v, Literal)}
    assert "превед" in value_set
    assert "бред" in value_set
