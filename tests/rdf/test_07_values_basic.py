"""Test 07: Statement value types - String, External-ID, URL"""
import pytest
from rdflib import Graph, URIRef, Literal
from .fixtures import load_json_entity, serialize_entity

def test_value_string():
    """Test string datatype value"""
    entity = load_json_entity("Q4")
    rdf_turtle = serialize_entity(entity)
    g = Graph().parse(data=rdf_turtle, format="turtle")
    
    # Find P7 statement (string type)
    stmt = [s for s in g.subjects() if "TEST-Statement-7-6063d202e584b79a2e9f89ab92b51e7f22ef9886" in str(s)][0]
    
    value = list(g.objects(subject=stmt, predicate=URIRef("http://www.wikidata.org/prop/statement/P7")))[0]
    
    assert isinstance(value, Literal), f"Expected Literal for string value, got {type(value)}"
    assert str(value) == "simplestring", f"Expected 'simplestring', got {value}"

def test_value_external_id():
    """Test external-id datatype value"""
    entity = load_json_entity("Q4")
    rdf_turtle = serialize_entity(entity)
    g = Graph().parse(data=rdf_turtle, format="turtle")
    
    # Find P11 statement (external-id type)
    stmt = [s for s in g.subjects() if "TEST-Statement-11-external-id" in str(s)][0]
    
    value = list(g.objects(subject=stmt, predicate=URIRef("http://www.wikidata.org/prop/statement/P11")))[0]
    
    assert isinstance(value, Literal), f"Expected Literal for external-id value"
    assert str(value) == "test-external-identifier"

def test_value_url():
    """Test URL datatype value"""
    entity = load_json_entity("Q4")
    rdf_turtle = serialize_entity(entity)
    g = Graph().parse(data=rdf_turtle, format="turtle")
    
    # Find P9 statement (URL type)
    stmt = [s for s in g.subjects() if "TEST-Statement-9-2669d541dfd2d6cc0105927bff02bbe0eec0e921" in str(s)][0]
    
    value = list(g.objects(subject=stmt, predicate=URIRef("http://www.wikidata.org/prop/statement/P9")))[0]
    
    assert isinstance(value, URIRef), f"Expected URIRef for URL value"
    # URL with special characters should be encoded
    assert "acme.test" in str(value), f"Expected 'acme.test' in URL, got {value}"
