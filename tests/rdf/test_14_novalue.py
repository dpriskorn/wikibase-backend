"""Test 14: Novalue statements (wdno:P3)"""
import pytest
from rdflib import Graph, URIRef
from .fixtures import load_json_entity, serialize_entity

def test_novalue_statement():
    """Test novalue statement generates wdno: triple"""
    entity = load_json_entity("Q4")
    rdf_turtle = serialize_entity(entity)
    g = Graph().parse(data=rdf_turtle, format="turtle")
    
    # Find the P3 novalue statement
    stmt = [s for s in g.subjects() if "TEST-Statement-3-12914044e0dbab210aa9d81168bd50471bbde12d" in str(s)][0]
    
    # Check that statement exists and has type
    assert (stmt, None, URIRef("http://wikiba.se/ontology#Statement")) in g
    
    # Check for novalue triple
    q4_uri = URIRef("http://www.wikidata.org/entity/Q4")
    novalue_triples = list(g.objects(subject=q4_uri, predicate=URIRef("http://www.wikidata.org/prop/novalue/P3")))
    
    assert len(novalue_triples) >= 1, f"Expected at least 1 wdno:P3 triple"
    
    # Check that novalue points to statement
    assert stmt in novalue_triples, f"Expected novalue to point to statement"