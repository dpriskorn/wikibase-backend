import json

from models.rdf_builder.converter import EntityToRdfConverter
from models.json_parser.entity_parser import parse_entity
from rdf.conftest import normalize_ttl, split_subject_blocks, TEST_DATA_DIR

def test_q120248304_matches_golden_ttl(property_registry):
    entity_id = "Q120248304"

    json_path = TEST_DATA_DIR / "json" / "entities" / f"{entity_id}.json"
    ttl_path = TEST_DATA_DIR / "rdf" / "ttl" / f"{entity_id}.ttl"

    entity_json = json.loads(json_path.read_text(encoding="utf-8"))
    expected_ttl = normalize_ttl(ttl_path.read_text(encoding="utf-8"))

    # ✅ use the real, already-working parser
    entity = parse_entity(entity_json)

    converter = EntityToRdfConverter(
        properties=property_registry
    )
    actual_ttl = normalize_ttl(converter.convert_to_string(entity))

    expected_blocks = split_subject_blocks(expected_ttl)
    actual_blocks = split_subject_blocks(actual_ttl)

    assert expected_blocks.keys() == actual_blocks.keys()

    for subject in expected_blocks:
        assert actual_blocks[subject] == expected_blocks[subject]
