from io import StringIO
from pathlib import Path

from models.internal_representation import Rank
from models.internal_representation.entity import Entity
from models.internal_representation.values.entity_value import EntityValue
from models.internal_representation.statements import Statement
from models.internal_representation.entity_types import EntityKind
from models.rdf_builder.converter import EntityConverter
from models.rdf_builder.property_registry.registry import PropertyRegistry
from models.rdf_builder.ontology.datatypes import property_shape

TEST_DATA_DIR = Path(__file__).parent.parent.parent / "test_data"


def test_collect_referenced_entities():
    """Test collecting entity IDs referenced in statements"""
    from models.internal_representation.values.entity_value import EntityValue
    from models.internal_representation.statements import Statement

    entity = Entity(
        id="Q1",
        type=EntityKind.ITEM,
        labels={},
        descriptions={},
        aliases={},
        statements=[
            Statement(
                property="P31",
                value=EntityValue(value="Q5"),
                rank=Rank.NORMAL,
                statement_id="Q1$1",
                qualifiers=[],
                references=[],
            ),
            Statement(
                property="P17",
                value=EntityValue(value="Q183"),
                rank=Rank.NORMAL,
                statement_id="Q1$2",
                qualifiers=[],
                references=[],
            ),
            Statement(
                property="P127",
                value=EntityValue(value="Q5"),
                rank=Rank.NORMAL,
                statement_id="Q1$3",
                qualifiers=[],
                references=[],
            ),
        ],
        sitelinks=None,
    )

    properties = {
        "P31": property_shape("P31", "wikibase-item"),
        "P17": property_shape("P17", "wikibase-item"),
        "P127": property_shape("P127", "wikibase-item"),
    }
    registry = PropertyRegistry(properties=properties)

    converter = EntityConverter(property_registry=registry)
    referenced = converter._collect_referenced_entities(entity)

    assert referenced == {"Q5", "Q183"}


def test_write_referenced_entity_metadata():
    """Test writing metadata for referenced entities"""
    entity_metadata_dir = TEST_DATA_DIR / "json" / "entities"

    main_entity = Entity(
        id="Q17948861",
        type=EntityKind.ITEM,
        labels={},
        descriptions={},
        aliases={},
        statements=[
            Statement(
                property="P31",
                value=EntityValue(value="Q17633526"),
                rank=Rank.NORMAL,
                statement_id="Q17948861$1",
                qualifiers=[],
                references=[],
            )
        ],
        sitelinks=None,
    )

    properties = {
        "P31": property_shape("P31", "wikibase-item"),
    }
    registry = PropertyRegistry(properties=properties)

    converter = EntityConverter(
        property_registry=registry, entity_metadata_dir=entity_metadata_dir
    )

    output = StringIO()
    converter._write_referenced_entity_metadata(main_entity, output)
    result = output.getvalue()

    assert "wd:Q17633526 a wikibase:Item" in result
    assert 'rdfs:label "Wikinews article"@en' in result
    assert 'schema:description "used with property P31"@en' in result


def test_load_referenced_entity_missing_file():
    """Test that missing referenced entity JSON raises FileNotFoundError"""
    entity_metadata_dir = TEST_DATA_DIR / "json" / "entities"

    properties = {
        "P31": property_shape("P31", "wikibase-item"),
    }
    registry = PropertyRegistry(properties=properties)

    converter = EntityConverter(
        property_registry=registry, entity_metadata_dir=entity_metadata_dir
    )

    try:
        converter._load_referenced_entity("Q999999")
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError as e:
        assert "Q999999" in str(e)


def test_converter_with_cache_path_generates_referenced_entity():
    """Test that EntityConverter with entity_metadata_dir generates referenced entity metadata"""
    entity_metadata_dir = TEST_DATA_DIR / "json" / "entities"

    entity_id = "Q17948861"
    json_path = entity_metadata_dir / f"{entity_id}.json"

    import json

    entity_json = json.loads(json_path.read_text(encoding="utf-8"))
    from models.json_parser.entity_parser import parse_entity

    entity = parse_entity(entity_json)

    properties = {
        "P31": property_shape("P31", "wikibase-item"),
    }
    registry = PropertyRegistry(properties=properties)

    converter = EntityConverter(
        property_registry=registry, entity_metadata_dir=entity_metadata_dir
    )
    actual_ttl = converter.convert_to_string(entity)

    assert "wd:Q17633526 a wikibase:Item" in actual_ttl
    assert 'rdfs:label "Wikinews article"@en' in actual_ttl
