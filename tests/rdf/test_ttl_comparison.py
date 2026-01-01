import json
import logging

import pytest

from conftest import normalize_ttl, split_subject_blocks, TEST_DATA_DIR
from models.rdf_builder.converter import EntityConverter
from models.json_parser.entity_parser import parse_entity
from models.rdf_builder.property_registry.registry import PropertyRegistry
from models.rdf_builder.ontology.datatypes import property_shape
from models.rdf_builder.uri_generator import URIGenerator

logger = logging.getLogger(__name__)


def test_q17948861_parse_and_generate():
    """Test parsing Q17948861 and generating TTL"""
    entity_id = "Q17948861"

    json_path = TEST_DATA_DIR / "json" / "entities" / f"{entity_id}.json"

    entity_json = json.loads(json_path.read_text(encoding="utf-8"))
    entity = parse_entity(entity_json)

    logger.info(f"Parsed entity: {entity.id}, type: {entity.type}")

    properties = {
        "P31": property_shape("P31", "wikibase-item"),
    }
    registry = PropertyRegistry(properties=properties)

    converter = EntityConverter(property_registry=registry)
    actual_ttl = converter.convert_to_string(entity)

    logger.info(f"Generated TTL length: {len(actual_ttl)}")

    assert len(actual_ttl) > 0
    assert "wd:Q17948861" in actual_ttl


def test_statement_uri_uses_dash_separator():
    """Test that statement URIs use - separator instead of $"""
    uri_gen = URIGenerator()
    statement_id = "Q17948861$FA20AC3A-5627-4EC5-93CA-24F0F00C8AA6"

    # Full URI
    full_uri = uri_gen.statement_uri(statement_id)
    assert (
        "$" not in full_uri
    ), f"Statement URI should not contain $ separator: {full_uri}"
    assert "-" in full_uri, f"Statement URI should use - separator: {full_uri}"
    assert "Q17948861-FA20AC3A-5627-4EC5-93CA-24F0F00C8AA6" in full_uri

    # Prefixed URI
    prefixed_uri = uri_gen.statement_prefixed(statement_id)
    assert (
        "$" not in prefixed_uri
    ), f"Prefixed statement URI should not contain $ separator: {prefixed_uri}"
    assert (
        "-" in prefixed_uri
    ), f"Prefixed statement URI should use - separator: {prefixed_uri}"
    assert "wds:Q17948861-FA20AC3A-5627-4EC5-93CA-24F0F00C8AA6" == prefixed_uri


@pytest.mark.skip("Disabled - blank node ID needs investigation")
def test_q17948861_roundtrip_comparison():
    """Test full roundtrip: JSON → TTL → normalize → compare to golden"""
    entity_id = "Q17948861"

    json_path = TEST_DATA_DIR / "json" / "entities" / f"{entity_id}.json"
    ttl_path = TEST_DATA_DIR / "rdf" / "ttl" / f"{entity_id}.ttl"

    # Parse JSON and generate TTL
    entity_json = json.loads(json_path.read_text(encoding="utf-8"))
    entity = parse_entity(entity_json)

    properties = {
        "P31": property_shape("P31", "wikibase-item"),
    }
    registry = PropertyRegistry(properties=properties)

    converter = EntityConverter(property_registry=registry)
    actual_ttl = converter.convert_to_string(entity)

    # Load golden TTL
    golden_ttl = ttl_path.read_text(encoding="utf-8")

    # Normalize both
    actual_normalized = normalize_ttl(actual_ttl)
    golden_normalized = normalize_ttl(golden_ttl)

    # Split into blocks
    actual_blocks = split_subject_blocks(actual_normalized)
    golden_blocks = split_subject_blocks(golden_normalized)

    logger.info(f"Actual blocks: {list(actual_blocks.keys())}")
    logger.info(f"Golden blocks: {list(golden_blocks.keys())}")

    # Compare
    assert actual_blocks.keys() == golden_blocks.keys()


@pytest.mark.skip("Disabled until missing features are implemented")
def test_q17948861_full_roundtrip():
    """Test full roundtrip: JSON → TTL → normalize → compare to golden"""
    entity_id = "Q17948861"

    json_path = TEST_DATA_DIR / "json" / "entities" / f"{entity_id}.json"
    ttl_path = TEST_DATA_DIR / "rdf" / "ttl" / f"{entity_id}.ttl"
    entity_metadata_dir = TEST_DATA_DIR / "entity_metadata"

    # Parse JSON and generate TTL
    entity_json = json.loads(json_path.read_text(encoding="utf-8"))
    entity = parse_entity(entity_json)

    properties = {
        "P31": property_shape("P31", "wikibase-item"),
    }
    registry = PropertyRegistry(properties=properties)

    converter = EntityConverter(
        property_registry=registry, entity_metadata_dir=entity_metadata_dir
    )
    actual_ttl = converter.convert_to_string(entity)

    # Load golden TTL
    golden_ttl = ttl_path.read_text(encoding="utf-8")

    # Normalize both
    actual_normalized = normalize_ttl(actual_ttl)
    golden_normalized = normalize_ttl(golden_ttl)

    # Split into blocks
    actual_blocks = split_subject_blocks(actual_normalized)
    golden_blocks = split_subject_blocks(golden_normalized)

    logger.info(f"Actual blocks: {list(actual_blocks.keys())}")
    logger.info(f"Golden blocks: {list(golden_blocks.keys())}")

    # Compare
    assert actual_blocks.keys() == golden_blocks.keys()
