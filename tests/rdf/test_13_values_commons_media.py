"""Test 13: Commons media values (Special:FilePath URLs)"""
import pytest
from rdflib import Graph, URIRef
from .fixtures import load_json_entity, serialize_entity

def test_value_commons_media():
    """Test commons media datatype produces Special:FilePath URL"""
    entity = load_json_entity("Q4")
    rdf_turtle = serialize_entity(entity)
    g = Graph().parse(data=rdf_turtle, format="turtle")
    
    # Find P3 statement (commonsMedia type with value)
    stmt = [s for s in g.subjects() if "TEST-Statement-3-b181ddac61642fe80bbf8e4a8aa1da425cb0ac9" in str(s)][0]
    
    value = list(g.objects(subject=stmt, predicate=URIRef("http://www.wikidata.org/prop/statement/P3")))[0]
    
    assert isinstance(value, URIRef), f"Expected URIRef for commons media value"
    assert "commons.wikimedia.org/wiki/Special:FilePath" in str(value), \
        f"Expected Special:FilePath URL in value, got {value}"
    assert "Universe.svg" in str(value), f"Expected 'Universe.svg' in filename"
