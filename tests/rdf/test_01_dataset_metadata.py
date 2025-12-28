"""Test 01: Dataset metadata generation"""
import pytest
from rdflib import Graph
from .fixtures import load_json_entity, load_expected_rdf, normalize_turtle

def test_q4_dataset_metadata(api_client, base_url):
    """Test that dataset metadata is correctly generated"""
    entity = load_json_entity("Q4")
    
    create_response = api_client.post(f"{base_url}/entity", json=entity)
    assert create_response.status_code == 200
    
    api_response = api_client.get(f"{base_url}/wiki/Special:EntityData/Q4.ttl")
    assert api_response.status_code == 200
    
    g_api = Graph().parse(data=api_response.text, format="turtle")
    
    # Check dataset node exists
    dataset_uri = g_api.value(None, None, None)  # Get subject
    assert dataset_uri, "Dataset node not found"
    
    # Check dataset type
    assert (dataset_uri, None, None) in g_api, "Dataset type not found"
    
    # Check required dataset properties
    dataset_triples = list(g_api.triples((dataset_uri, None, None)))
    assert len(dataset_triples) >= 4, f"Expected at least 4 dataset triples, got {len(dataset_triples)}"
    
    # Check about, license, softwareVersion, dateModified
    predicates_found = {str(p) for s, p, o in dataset_triples}
    required_predicates = [
        "http://schema.org/about",
        "http://creativecommons.org/ns#license",
        "http://schema.org/softwareVersion",
        "http://schema.org/dateModified"
    ]
    
    for pred in required_predicates:
        assert pred in predicates_found, f"Missing predicate: {pred}"
