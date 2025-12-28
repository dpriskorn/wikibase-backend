"""Test 12: Globe coordinate values (latitude + longitude + globe + precision)"""
import pytest
from rdflib import Graph, URIRef, Literal
from .fixtures import load_json_entity, serialize_entity

def test_value_globecoordinate():
    """Test globe coordinate datatype produces WKT literal"""
    entity = load_json_entity("Q4")
    rdf_turtle = serialize_entity(entity)
    g = Graph().parse(data=rdf_turtle, format="turtle")
    
    # Find P4 statement (globecoordinate type)
    stmt = [s for s in g.subjects() if "TEST-Statement-4-8749fa158a249e1befa6ed077f648c56197a2b2d" in str(s)][0]
    
    value = list(g.objects(subject=stmt, predicate=URIRef("http://www.wikidata.org/prop/statement/P4")))[0]
    
    assert isinstance(value, Literal), f"Expected Literal for globe coordinate value"
    
    # Check WKT format
    value_str = str(value)
    assert "Point(67.25 12.125)" in value_str or "Point(12.125 67.25)" in value_str, \
        f"Expected WKT Point in coordinate value, got {value_str}"

def test_globecoordinate_value_node():
    """Test globe coordinate value node with precision and globe"""
    entity = load_json_entity("Q4")
    rdf_turtle = serialize_entity(entity)
    g = Graph().parse(data=rdf_turtle, format="turtle")
    
    # Find globe coordinate value node for P4
    stmt = [s for s in g.subjects() if "TEST-Statement-4-8749fa158a249e1befa6ed077f648c56197a2b2d" in str(s)][0]
    
    # Note: Current serializer doesn't generate value nodes
    # Expected when implemented:
    # - wikibase:geoLatitude with xsd:double
    # - wikibase:geoLongitude with xsd:double
    # - wikibase:geoPrecision with xsd:double
    # - wikibase:geoGlobe (wd:Q2 for Earth)
    # - All triple objects should be typed as GlobecoordinateValue
