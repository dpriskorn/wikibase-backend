"""Test 08: Wikibase item values (wd:Q42, wd:Q666)"""
import pytest
from rdflib import Graph, URIRef
from .fixtures import load_json_entity, serialize_entity

def test_value_wikibase_item():
    """Test wikibase-item datatype produces entity URI"""
    entity = load_json_entity("Q4")
    rdf_turtle = serialize_entity(entity)
    g = Graph().parse(data=rdf_turtle, format="turtle")
    
    # Find P2 statement (wikibase-item)
    stmt = [s for s in g.subjects() if "TEST-Statement-2-423614cd831ed4e8da1138c9229cb65cf96f9366" in str(s)][0]
    
    value = list(g.objects(subject=stmt, predicate=URIRef("http://www.wikidata.org/prop/statement/P2")))[0]
    
    assert value == URIRef("http://www.wikidata.org/entity/Q42"), \
        f"Expected wd:Q42, got {value}"

def test_multiple_wikibase_item_values():
    """Test multiple wikibase-item values for same property"""
    entity = load_json_entity("Q4")
    rdf_turtle = serialize_entity(entity)
    g = Graph().parse(data=rdf_turtle, format="turtle")
    
    q4_uri = URIRef("http://www.wikidata.org/entity/Q4")
    
    # Get all P2 values
    p2_values = list(g.objects(subject=q4_uri, predicate=URIRef("http://www.wikidata.org/prop/direct/P2")))
    
    assert len(p2_values) == 2, f"Expected 2 direct P2 values"
    assert URIRef("http://www.wikidata.org/entity/Q42") in p2_values
    assert URIRef("http://www.wikidata.org/entity/Q666") in p2_values
