"""Test 06: Basic statement structure (p:P2 wds:Q42-$UUID)"""
import pytest
from rdflib import Graph, URIRef
from .fixtures import load_json_entity, serialize_entity

def test_q4_statement_uris():
    """Test statement URIs are correctly generated"""
    entity = load_json_entity("Q4")
    rdf_turtle = serialize_entity(entity)
    g = Graph().parse(data=rdf_turtle, format="turtle")
    
    q4_uri = URIRef("http://www.wikidata.org/entity/Q4")
    
    # Get all statement URIs from p:P2
    p2_statements = list(g.objects(subject=q4_uri, predicate=URIRef("http://www.wikidata.org/prop/P2")))
    
    assert len(p2_statements) == 2, f"Expected 2 P2 statements, got {len(p2_statements)}"
    
    # Check statements start with correct prefix
    for stmt in p2_statements:
        assert str(stmt).startswith("http://www.wikidata.org/entity/statement/TEST-"), \
            f"Statement URI should start with wds:, got: {stmt}"

def test_q4_statement_types():
    """Test statements have wikibase:Statement type"""
    entity = load_json_entity("Q4")
    rdf_turtle = serialize_entity(entity)
    g = Graph().parse(data=rdf_turtle, format="turtle")
    
    # Check that all statements have Statement type
    for stmt in g.subjects():
        if "entity/statement/TEST-" in str(stmt):
            assert (stmt, None, URIRef("http://wikiba.se/ontology#Statement")) in g, \
                f"Statement {stmt} missing wikibase:Statement type"

def test_q4_statement_ranks_normal():
    """Test normal rank statements"""
    entity = load_json_entity("Q4")
    rdf_turtle = serialize_entity(entity)
    g = Graph().parse(data=rdf_turtle, format="turtle")
    
    # Find the normal rank P2 statement
    normal_stmt = [s for s in g.subjects() if "TEST-Statement-2-475ae31b07cff4f0e33531030b1ba58f004fcd4b" in str(s)][0]
    
    rank_triples = list(g.objects(subject=normal_stmt, predicate=URIRef("http://wikiba.se/ontology#rank")))
    assert len(rank_triples) == 1, f"Expected 1 rank triple"
    assert rank_triples[0] == URIRef("http://wikiba.se/ontology#NormalRank"), \
        f"Expected NormalRank, got {rank_triples[0]}"

def test_q4_statement_ranks_preferred():
    """Test preferred rank statements"""
    entity = load_json_entity("Q4")
    rdf_turtle = serialize_entity(entity)
    g = Graph().parse(data=rdf_turtle, format="turtle")
    
    # Find the preferred rank P2 statement
    preferred_stmt = [s for s in g.subjects() if "TEST-Statement-2-423614cd831ed4e8da1138c9229cb65cf96f9366" in str(s)][0]
    
    rank_triples = list(g.objects(subject=preferred_stmt, predicate=URIRef("http://wikiba.se/ontology#rank")))
    assert len(rank_triples) == 1, f"Expected 1 rank triple"
    assert rank_triples[0] == URIRef("http://wikiba.se/ontology#PreferredRank")

def test_q4_statement_ranks_deprecated():
    """Test deprecated rank statements (P5 has a deprecated statement)"""
    entity = load_json_entity("Q4")
    rdf_turtle = serialize_entity(entity)
    g = Graph().parse(data=rdf_turtle, format="turtle")
    
    # Find the deprecated rank P5 statement
    deprecated_stmt = [s for s in g.subjects() if "TEST-Statement-5-b27fe5a95fa506ca99acebd9e97c9c5a81e14f99" in str(s)][0]
    
    rank_triples = list(g.objects(subject=deprecated_stmt, predicate=URIRef("http://wikiba.se/ontology#rank")))
    assert len(rank_triples) == 1, f"Expected 1 rank triple"
    assert rank_triples[0] == URIRef("http://wikiba.se/ontology#DeprecatedRank")

def test_q4_bestrank_assertions():
    """Test BestRank assertions on statements"""
    entity = load_json_entity("Q4")
    rdf_turtle = serialize_entity(entity)
    g = Graph().parse(data=rdf_turtle, format="turtle")
    
    # Check all statements have BestRank type
    for stmt in g.subjects():
        if "entity/statement/TEST-" in str(stmt):
            assert (stmt, None, URIRef("http://wikiba.se/ontology#BestRank")) in g, \
                f"Statement {stmt} missing wikibase:BestRank type"
