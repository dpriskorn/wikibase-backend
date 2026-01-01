import json
import logging

from conftest import TEST_DATA_DIR
from models.json_parser.entity_parser import parse_entity
from models.rdf_builder.converter import EntityConverter

logger = logging.getLogger(__name__)


def test_q120248304_conversion(full_property_registry):
    """Test Q120248304 (medium entity) conversion produces valid Turtle"""
    entity_id = "Q120248304"

    json_path = TEST_DATA_DIR / "json" / "entities" / f"{entity_id}.json"

    entity_json = json.loads(json_path.read_text(encoding="utf-8"))
    entity = parse_entity(entity_json)

    logger.info(f"Parsed entity: {entity.id}, statements: {len(entity.statements)}")

    for stmt in entity.statements:
        logger.debug(f"  Property: {stmt.property}, Rank: {stmt.rank}")

    converter = EntityConverter(property_registry=full_property_registry)
    actual_ttl = converter.convert_to_string(entity)

    logger.info(f"Generated TTL length: {len(actual_ttl)}")

    p625_shape = (
        full_property_registry.shape("P625")
        if "P625" in [s.property for s in entity.statements]
        else None
    )
    if p625_shape:
        logger.debug(f"P625 shape: {p625_shape}")

    if "ps:P625" in actual_ttl or "Point" in actual_ttl:
        for line in actual_ttl.split("\n"):
            if "P625" in line or "Point" in line:
                logger.debug(f"P625/Point line: {line}")

    # Basic validation
    assert len(actual_ttl) > 0
    assert "wd:Q120248304" in actual_ttl

    # Check statement URIs use wds: prefix with dash separator
    assert "wds:Q120248304-4DFA2BE2-34CB-442E-B364-D01FE69A2FB5" in actual_ttl
    assert "$" not in actual_ttl, "Statement URIs should not contain $ separator"

    # Check reference URIs use wdref: prefix with hash
    assert "wdref:ba8e2620a184969d3dfc41448810665dc67de68e" in actual_ttl

    # Check some statement values
    assert "ps:P17 wd:Q142" in actual_ttl
    assert 'ps:P11840 "I621930023"' in actual_ttl
    # Globe coordinate now uses value node (psv:P625 -> wdv:xxx)
    assert "psv:P625 wdv:" in actual_ttl
    assert "wikibase:GlobecoordinateValue" in actual_ttl
    assert 'wikibase:geoLatitude "50.94636"^^xsd:double' in actual_ttl
    assert 'wikibase:geoLongitude "1.88108"^^xsd:double' in actual_ttl

    logger.info("Q120248304 conversion test passed!")
