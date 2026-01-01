"""Integration test for value node deduplication in entity conversion."""

import json
import logging
import re

from conftest import TEST_DATA_DIR, full_property_registry
from models.json_parser.entity_parser import parse_entity
from models.rdf_builder.converter import EntityConverter

logger = logging.getLogger(__name__)


def test_q120248304_no_duplicate_value_nodes(full_property_registry):
    """Test that duplicate value nodes are not written for Q120248304."""
    entity_id = "Q120248304"

    json_path = TEST_DATA_DIR / "json" / "entities" / f"{entity_id}.json"
    entity_json = json.loads(json_path.read_text(encoding="utf-8"))
    entity = parse_entity(entity_json)

    converter = EntityConverter(property_registry=full_property_registry)
    actual_ttl = converter.convert_to_string(entity)

    # Count wdv: BLOCK definitions (each should appear once)
    wdv_blocks = re.findall(r"wdv:([a-f0-9]{32})\s+a wikibase:", actual_ttl)

    # Each unique value node should be written exactly ONCE
    unique_block_ids = set(wdv_blocks)
    assert len(wdv_blocks) == len(
        unique_block_ids
    ), f"Each unique value node should be written once. Blocks: {wdv_blocks}"

    logger.info(
        f"Q42: {len(wdv_blocks)} wdv blocks written (should equal unique values)"
    )

    # Verify deduplication is working (prevented duplicate blocks)
    if converter.dedupe:
        stats = converter.dedupe.stats()
        logger.info(f"Deduplication stats: {stats}")
        assert (
            stats["hits"] > 0
        ), f"Deduplication prevented {stats['hits']} duplicate block writes"


def test_deduplication_stats(full_property_registry):
    """Test that deduplication statistics are tracked."""
    entity_id = "Q120248304"

    json_path = TEST_DATA_DIR / "json" / "entities" / f"{entity_id}.json"
    entity_json = json.loads(json_path.read_text(encoding="utf-8"))
    entity = parse_entity(entity_json)

    converter = EntityConverter(property_registry=full_property_registry)
    converter.convert_to_string(entity)

    # Check stats are available
    if converter.dedupe:
        stats = converter.dedupe.stats()
        logger.info(f"Deduplication stats: {stats}")

        assert stats["hits"] >= 0
        assert stats["misses"] >= 0
        assert stats["size"] >= 0
        assert 0 <= stats["collision_rate"] <= 100


def test_deduplication_disabled(full_property_registry):
    """Test that deduplication can be disabled."""
    entity_id = "Q120248304"

    json_path = TEST_DATA_DIR / "json" / "entities" / f"{entity_id}.json"
    entity_json = json.loads(json_path.read_text(encoding="utf-8"))
    entity = parse_entity(entity_json)

    # Create converter with deduplication disabled
    converter = EntityConverter(
        property_registry=full_property_registry, enable_deduplication=False
    )

    assert converter.dedupe is None, "Dedupe should be None when disabled"

    # Should still generate valid TTL
    actual_ttl = converter.convert_to_string(entity)
    assert len(actual_ttl) > 0
    assert "wd:Q120248304" in actual_ttl


def test_q42_no_duplicate_value_nodes(full_property_registry):
    """Test that Q42 (large entity) has no duplicate value nodes."""
    entity_id = "Q42"

    json_path = TEST_DATA_DIR / "json" / "entities" / f"{entity_id}.json"
    entity_json = json.loads(json_path.read_text(encoding="utf-8"))
    entity = parse_entity(entity_json)

    converter = EntityConverter(property_registry=full_property_registry)
    actual_ttl = converter.convert_to_string(entity)

    # Count only value node BLOCK definitions (wdv:xxx a wikibase:Type)
    wdv_ids = re.findall(r"wdv:([a-f0-9]{32})\s+a wikibase:", actual_ttl)
    unique_ids = set(wdv_ids)

    logger.info(f"Q42: {len(wdv_ids)} total wdv: blocks, {len(unique_ids)} unique")

    # No duplicates
    assert len(wdv_ids) == len(unique_ids), "Q42 should have no duplicate value nodes"
