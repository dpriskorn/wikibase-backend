"""Test 11: Quantity values (amount + unit + bounds)"""
import pytest
from rdflib import Graph, URIRef, Literal, XSD
from .fixtures import load_json_entity, serialize_entity

def test_value_quantity():
    """Test quantity datatype produces decimal literal"""
    entity = load_json_entity("Q4")
    rdf_turtle = serialize_entity(entity)
    g = Graph().parse(data=rdf_turtle, format="turtle")
    
    # Find P6 statement (quantity type)
    stmt = [s for s in g.subjects() if "TEST-Statement-6-9ae284048af6d9ab0f2815ef104216cb8b22e8bc" in str(s)][0]
    
    value = list(g.objects(subject=stmt, predicate=URIRef("http://www.wikidata.org/prop/statement/P6")))[0]
    
    assert isinstance(value, Literal), f"Expected Literal for quantity value"
    assert value.datatype == XSD.decimal, f"Expected xsd:decimal datatype"
    
    # Check the amount value (should be the main value)
    value_str = str(value)
    assert "19.768" in value_str, f"Expected 19.768 in quantity value, got {value_str}"

def test_quantity_value_node():
    """Test quantity value node with unit and bounds"""
    entity = load_json_entity("Q4")
    rdf_turtle = serialize_entity(entity)
    g = Graph().parse(data=rdf_turtle, format="turtle")
    
    # Find quantity value node for P6
    stmt = [s for s in g.subjects() if "TEST-Statement-6-9ae284048af6d9ab0f2815ef104216cb8b22e8bc" in str(s)][0]
    
    # Note: Current serializer doesn't generate value nodes
    # This test documents the expected behavior
    
    # When value nodes are implemented, they should have:
    # - wikibase:quantityAmount with the decimal amount
    # - wikibase:quantityUnit (wd:Q199 for "1" unit)
    # - wikibase:quantityLowerBound with decimal
    # - wikibase:quantityUpperBound with decimal
    # - wikibase:quantityNormalized
    # All with xsd:decimal datatypes
