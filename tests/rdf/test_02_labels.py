"""Test 02: Label generation (rdfs:label, skos:prefLabel, schema:name)"""
import pytest
from rdflib import Graph, URIRef, Literal
from .fixtures import load_json_entity, load_expected_rdf, serialize_entity

def test_q2_single_label_en():
    """Test single English label generates three label triples"""
    entity = load_json_entity("Q2")
    rdf_turtle = serialize_entity(entity)
    g = Graph().parse(data=rdf_turtle, format="turtle")
    
    q2_uri = URIRef("http://www.wikidata.org/entity/Q2")
    
    # Check for rdfs:label
    rdfs_labels = list(g.objects(subject=q2_uri, predicate=URIRef("http://www.w3.org/2000/01/rdf-schema#label")))
    assert len(rdfs_labels) >= 1, "Missing rdfs:label"
    
    en_label = [l for l in rdfs_labels if l.language == "en"]
    assert len(en_label) == 1, f"Expected 1 English rdfs:label, got {len(en_label)}"
    assert en_label[0].value == "Berlin", f"Expected 'Berlin', got {en_label[0].value}"
    
    # Check for skos:prefLabel
    skos_labels = list(g.objects(subject=q2_uri, predicate=URIRef("http://www.w3.org/2004/02/skos/core#prefLabel")))
    assert len(skos_labels) >= 1, "Missing skos:prefLabel"
    
    en_preflabel = [l for l in skos_labels if l.language == "en"]
    assert len(en_preflabel) == 1, f"Expected 1 English skos:prefLabel"
    assert en_preflabel[0].value == "Berlin"
    
    # Check for schema:name
    schema_names = list(g.objects(subject=q2_uri, predicate=URIRef("http://schema.org/name")))
    assert len(schema_names) >= 1, "Missing schema:name"
    
    en_schemaname = [n for n in schema_names if n.language == "en"]
    assert len(en_schemaname) == 1, f"Expected 1 English schema:name"
    assert en_schemaname[0].value == "Berlin"

def test_q2_multi_language_labels():
    """Test labels in multiple languages"""
    entity = load_json_entity("Q2")
    rdf_turtle = serialize_entity(entity)
    g = Graph().parse(data=rdf_turtle, format="turtle")
    
    q2_uri = URIRef("http://www.wikidata.org/entity/Q2")
    
    rdfs_labels = list(g.objects(subject=q2_uri, predicate=URIRef("http://www.w3.org/2000/01/rdf-schema#label")))
    label_languages = {l.language for l in rdfs_labels if l.language}
    
    assert "en" in label_languages, "Missing English label"
    assert "ru" in label_languages, "Missing Russian label"
    assert len(label_languages) >= 2, f"Expected at least 2 languages, got {len(label_languages)}"

def test_empty_labels():
    """Test entity with no labels"""
    entity = {
        "id": "Q99999",
        "type": "item",
        "labels": {}
    }
    rdf_turtle = serialize_entity(entity)
    g = Graph().parse(data=rdf_turtle, format="turtle")
    
    q99999_uri = URIRef("http://www.wikidata.org/entity/Q99999")
    rdfs_labels = list(g.objects(subject=q99999_uri, predicate=URIRef("http://www.w3.org/2000/01/rdf-schema#label")))
    assert len(rdfs_labels) == 0, f"Expected 0 labels for entity with empty labels dict"
