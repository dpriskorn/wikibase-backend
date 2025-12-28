"""Test 05: Direct property triples (wdt:P2 wd:Q42)"""
import pytest
from rdflib import Graph, URIRef
from .fixtures import load_json_entity, serialize_entity

def test_q4_direct_properties():
    """Test direct property triples for all property types in Q4"""
    entity = load_json_entity("Q4")
    rdf_turtle = serialize_entity(entity)
    g = Graph().parse(data=rdf_turtle, format="turtle")
    
    q4_uri = URIRef("http://www.wikidata.org/entity/Q4")
    
    # Check P2 (wikibase-item)
    p2_direct = list(g.objects(subject=q4_uri, predicate=URIRef("http://www.wikidata.org/prop/direct/P2")))
    assert len(p2_direct) == 2, f"Expected 2 wd:P2 triples, got {len(p2_direct)}"
    assert URIRef("http://www.wikidata.org/entity/Q42") in p2_direct
    assert URIRef("http://www.wikidata.org/entity/Q666") in p2_direct
    
    # Check P3 (commonsMedia) - should have direct triple and novalue triple
    p3_direct = list(g.objects(subject=q4_uri, predicate=URIRef("http://www.wikidata.org/prop/direct/P3")))
    assert URIRef("http://commons.wikimedia.org/wiki/Special:FilePath/Universe.svg") in p3_direct
    
    # Check for novalue triple (one of P3 statements has snaktype=novalue)
    p3_novalue = list(g.objects(subject=q4_uri, predicate=URIRef("http://www.wikidata.org/prop/novalue/P3")))
    assert len(p3_novalue) >= 1, "Missing wdno:P3 triple for novalue statement"

def test_q4_direct_external_id():
    """Test direct property for external-id datatype"""
    entity = load_json_entity("Q4")
    rdf_turtle = serialize_entity(entity)
    g = Graph().parse(data=rdf_turtle, format="turtle")
    
    q4_uri = URIRef("http://www.wikidata.org/entity/Q4")
    
    p11_direct = list(g.objects(subject=q4_uri, predicate=URIRef("http://www.wikidata.org/prop/direct/P11")))
    assert len(p11_direct) == 1, f"Expected 1 wd:P11 triple"
    assert str(p11_direct[0]) == "test-external-identifier", f"Expected 'test-external-identifier', got {p11_direct[0]}"

def test_q4_direct_string():
    """Test direct property for string datatype"""
    entity = load_json_entity("Q4")
    rdf_turtle = serialize_entity(entity)
    g = Graph().parse(data=rdf_turtle, format="turtle")
    
    q4_uri = URIRef("http://www.wikidata.org/entity/Q4")
    
    p7_direct = list(g.objects(subject=q4_uri, predicate=URIRef("http://www.wikidata.org/prop/direct/P7")))
    assert len(p7_direct) == 1, f"Expected 1 wd:P7 triple"
    assert str(p7_direct[0]) == "simplestring", f"Expected 'simplestring', got {p7_direct[0]}"
