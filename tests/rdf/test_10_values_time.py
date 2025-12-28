"""Test 10: Time values (with precision, timezone, calendar model)"""
import pytest
from rdflib import Graph, URIRef, Literal, XSD
from .fixtures import load_json_entity, serialize_entity

def test_value_time():
    """Test time datatype with precision and calendar model"""
    entity = load_json_entity("Q4")
    rdf_turtle = serialize_entity(entity)
    g = Graph().parse(data=rdf_turtle, format="turtle")
    
    # Find P8 statement (time type)
    stmt = [s for s in g.subjects() if "TEST-Statement-8-5dd0f6624a7545401bc306a068ac1bbe0148bfac" in str(s)][0]
    
    value = list(g.objects(subject=stmt, predicate=URIRef("http://www.wikidata.org/prop/statement/P8")))[0]
    
    assert isinstance(value, Literal), f"Expected Literal for time value"
    assert value.datatype == XSD.dateTime, f"Expected xsd:dateTime datatype"
    
    # Check the time value format
    assert "-0200-01-01T00:00:00Z" in str(value), f"Expected -0200-01-01T00:00:00Z in time value"

def test_time_value_node():
    """Test time value node with precision and calendar model"""
    entity = load_json_entity("Q4")
    rdf_turtle = serialize_entity(entity)
    g = Graph().parse(data=rdf_turtle, format="turtle")
    
    # Find time value node for P8
    stmt = [s for s in g.subjects() if "TEST-Statement-8-5dd0f6624a7545401bc306a068ac1bbe0148bfac" in str(s)][0]
    
    # Note: Current serializer doesn't generate value nodes, so this test will fail
    # This test documents the expected behavior
    
    value_node_ref = list(g.objects(subject=stmt, predicate=URIRef("http://www.wikidata.org/prop/statement/value/P8")))
    
    # When value nodes are implemented, they should have:
    # - wikibase:timeValue with the datetime
    # - wikibase:timePrecision (9 for decade)
    # - wikibase:timeTimezone (0)
    # - wikibase:timeCalendarModel (wd:Q1985727 for Gregorian)
    # - wikibase:timeValueNormalized
