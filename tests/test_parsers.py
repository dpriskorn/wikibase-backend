import json
from pathlib import Path

import pytest

from services.shared.parsers import parse_entity, parse_statement, parse_value

TEST_DATA_DIR = Path(__file__).parent.parent / "test_data"


def test_parse_entity_value():
    """Test parsing entity value (Q42, P31)"""
    snak_json = {
        "snaktype": "value",
        "property": "P31",
        "datatype": "wikibase-item",
        "datavalue": {
            "value": {"entity-type": "item", "numeric-id": 42, "id": "Q42"},
            "type": "wikibase-entityid"
        }
    }

    value = parse_value(snak_json)
    assert value.kind == "entity"
    assert value.value == "Q42"
    assert value.datatype_uri == "http://wikiba.se/ontology#WikibaseItem"


def test_parse_string_value():
    """Test parsing string value"""
    snak_json = {
        "snaktype": "value",
        "property": "P1",
        "datatype": "string",
        "datavalue": {
            "value": "test string",
            "type": "string"
        }
    }

    value = parse_value(snak_json)
    assert value.kind == "string"
    assert value.value == "test string"
    assert value.datatype_uri == "http://wikiba.se/ontology#String"


def test_parse_time_value():
    """Test parsing time value"""
    snak_json = {
        "snaktype": "value",
        "property": "P5",
        "datatype": "time",
        "datavalue": {
            "value": {
                "time": "+2023-12-31T00:00:00Z",
                "timezone": 0,
                "before": 0,
                "after": 0,
                "precision": 11,
                "calendarmodel": "http://www.wikidata.org/entity/Q1985727"
            },
            "type": "time"
        }
    }

    value = parse_value(snak_json)
    assert value.kind == "time"
    assert value.value == "+2023-12-31T00:00:00Z"
    assert value.timezone == 0
    assert value.precision == 11


def test_parse_quantity_value():
    """Test parsing quantity value"""
    snak_json = {
        "snaktype": "value",
        "property": "P6",
        "datatype": "quantity",
        "datavalue": {
            "value": {
                "amount": "+34.5",
                "unit": "1",
                "upperBound": "+35.3",
                "lowerBound": "+33.7"
            },
            "type": "quantity"
        }
    }

    value = parse_value(snak_json)
    assert value.kind == "quantity"
    assert value.value == "+34.5"
    assert value.unit == "1"
    assert value.upper_bound == "+35.3"
    assert value.lower_bound == "+33.7"


def test_parse_globe_value():
    """Test parsing globe coordinate value"""
    snak_json = {
        "snaktype": "value",
        "property": "P7",
        "datatype": "globecoordinate",
        "datavalue": {
            "value": {
                "latitude": 67.25,
                "longitude": 12.125,
                "altitude": None,
                "precision": 1 / 3600,
                "globe": "http://www.wikidata.org/entity/Q2"
            },
            "type": "globecoordinate"
        }
    }

    value = parse_value(snak_json)
    assert value.kind == "globe"
    assert value.latitude == 67.25
    assert value.longitude == 12.125


def test_parse_monolingual_value():
    """Test parsing monolingual text value"""
    snak_json = {
        "snaktype": "value",
        "property": "P8",
        "datatype": "monolingualtext",
        "datavalue": {
            "value": {
                "text": "Douglas Adams",
                "language": "en"
            },
            "type": "monolingualtext"
        }
    }

    value = parse_value(snak_json)
    assert value.kind == "monolingual"
    assert value.language == "en"
    assert value.text == "Douglas Adams"


def test_parse_external_id_value():
    """Test parsing external ID value"""
    snak_json = {
        "snaktype": "value",
        "property": "P9",
        "datatype": "external-id",
        "datavalue": {
            "value": "12345",
            "type": "string"
        }
    }

    value = parse_value(snak_json)
    assert value.kind == "external_id"
    assert value.value == "12345"


def test_parse_commons_media_value():
    """Test parsing commons media value"""
    snak_json = {
        "snaktype": "value",
        "property": "P10",
        "datatype": "commonsMedia",
        "datavalue": {
            "value": "Example.jpg",
            "type": "string"
        }
    }

    value = parse_value(snak_json)
    assert value.kind == "commons_media"
    assert value.value == "Example.jpg"


def test_parse_geo_shape_value():
    """Test parsing geo shape value"""
    snak_json = {
        "snaktype": "value",
        "property": "P11",
        "datatype": "geo-shape",
        "datavalue": {
            "value": "Data:Example.map",
            "type": "string"
        }
    }

    value = parse_value(snak_json)
    assert value.kind == "geo_shape"
    assert value.value == "Data:Example.map"


def test_parse_tabular_data_value():
    """Test parsing tabular data value"""
    snak_json = {
        "snaktype": "value",
        "property": "P12",
        "datatype": "tabular-data",
        "datavalue": {
            "value": "Data:Example.tab",
            "type": "string"
        }
    }

    value = parse_value(snak_json)
    assert value.kind == "tabular_data"
    assert value.value == "Data:Example.tab"


def test_parse_musical_notation_value():
    """Test parsing musical notation value"""
    snak_json = {
        "snaktype": "value",
        "property": "P13",
        "datatype": "musical-notation",
        "datavalue": {
            "value": "\\relative c' { c d e f }",
            "type": "string"
        }
    }

    value = parse_value(snak_json)
    assert value.kind == "musical_notation"
    assert value.value == "\\relative c' { c d e f }"


def test_parse_url_value():
    """Test parsing URL value"""
    snak_json = {
        "snaktype": "value",
        "property": "P14",
        "datatype": "url",
        "datavalue": {
            "value": "https://example.com",
            "type": "string"
        }
    }

    value = parse_value(snak_json)
    assert value.kind == "url"
    assert value.value == "https://example.com"


def test_parse_math_value():
    """Test parsing math value"""
    snak_json = {
        "snaktype": "value",
        "property": "P15",
        "datatype": "math",
        "datavalue": {
            "value": "E = mc^2",
            "type": "string"
        }
    }

    value = parse_value(snak_json)
    assert value.kind == "math"
    assert value.value == "E = mc^2"


def test_parse_entity_schema_value():
    """Test parsing entity schema value"""
    snak_json = {
        "snaktype": "value",
        "property": "P16",
        "datatype": "entity-schema",
        "datavalue": {
            "value": "S1234",
            "type": "string"
        }
    }

    value = parse_value(snak_json)
    assert value.kind == "entity_schema"
    assert value.value == "S1234"


def test_parse_statement_basic():
    """Test parsing basic statement"""
    statement_json = {
        "mainsnak": {
            "snaktype": "value",
            "property": "P31",
            "datatype": "wikibase-item",
            "datavalue": {
                "value": {"entity-type": "item", "numeric-id": 5, "id": "Q5"},
                "type": "wikibase-entityid"
            }
        },
        "type": "statement",
        "id": "Q42-F078E5B3-F9A8-480E-B7AC-D97778CBBEF9",
        "rank": "normal",
        "qualifiers": {},
        "references": []
    }

    statement = parse_statement(statement_json)
    assert statement.property == "P31"
    assert statement.value.kind == "entity"
    assert statement.value.value == "Q5"
    assert statement.rank == "normal"
    assert statement.statement_id == "Q42-F078E5B3-F9A8-480E-B7AC-D97778CBBEF9"
    assert len(statement.qualifiers) == 0
    assert len(statement.references) == 0


def test_parse_entity_basic():
    """Test parsing basic entity"""
    entity_json = {
        "id": "Q42",
        "type": "item",
        "labels": {
            "en": {"language": "en", "value": "Douglas Adams"}
        },
        "descriptions": {
            "en": {"language": "en", "value": "English author"}
        },
        "aliases": {
            "en": [{"language": "en", "value": "DA"}]
        },
        "claims": {}
    }

    entity = parse_entity(entity_json)
    assert entity.id == "Q42"
    assert entity.type == "item"
    assert entity.labels == {"en": "Douglas Adams"}
    assert entity.descriptions == {"en": "English author"}
    assert entity.aliases == {"en": ["DA"]}
    assert len(entity.statements) == 0
    assert entity.sitelinks is None


def test_parse_q1_minimal():
    """Test parsing minimal entity with only id and type"""
    with open(TEST_DATA_DIR / "entities/Q1.json") as f:
        entity_json = json.load(f)

    entity = parse_entity(entity_json)
    assert entity.id == "Q1"
    assert entity.type == "item"
    assert entity.labels == {}
    assert entity.descriptions == {}
    assert entity.aliases == {}
    assert entity.statements == []
    assert entity.sitelinks is None


def test_parse_q42():
    """Test parsing Douglas Adams entity from real test data"""
    with open(TEST_DATA_DIR / "entities/Q42.json") as f:
        entity_json = json.load(f)

    entity = parse_entity(entity_json)
    assert entity.id == "Q42"
    assert entity.type == "item"
    assert "en" in entity.labels
    assert entity.labels["en"] == "Douglas Adams"
    assert len(entity.statements) > 0


def test_parse_q42_detailed():
    """Test parsing Q42 with detailed verification of content"""
    with open(TEST_DATA_DIR / "entities/Q42.json") as f:
        data = json.load(f)

    entity_json = data["entities"]["Q42"]
    entity = parse_entity(entity_json)
    assert entity.id == "Q42"
    assert entity.type == "item"

    assert len(entity.labels) > 100
    assert "en" in entity.labels
    assert "ru" in entity.labels

    assert len(entity.statements) > 300

    p31_statements = [stmt for stmt in entity.statements if stmt.property == "P31"]
    assert len(p31_statements) > 0
    assert any(stmt.value.kind == "entity" for stmt in p31_statements)

    ranks = [stmt.rank.value for stmt in entity.statements]
    assert "normal" in ranks
    assert "preferred" in ranks

    has_sitelinks = entity.sitelinks is not None and len(entity.sitelinks) > 0
    assert has_sitelinks


def test_parse_p2():
    """Test parsing property entity from real test data"""
    with open(TEST_DATA_DIR / "entities/P2.json") as f:
        entity_json = json.load(f)

    entity = parse_entity(entity_json)
    assert entity.id == "P2"
    assert entity.type == "property"
    assert len(entity.labels) > 0
    assert len(entity.statements) > 0


def test_parse_q2_multilingual():
    """Test parsing entity with multilingual labels, descriptions, and aliases"""
    with open(TEST_DATA_DIR / "entities/Q2.json") as f:
        entity_json = json.load(f)

    entity = parse_entity(entity_json)
    assert entity.id == "Q2"
    assert entity.type == "item"
    assert entity.labels == {"en": "Berlin", "ru": "Берлин"}
    assert entity.descriptions == {"en": "German city", "ru": "столица и одновременно земля Германии"}
    assert entity.aliases == {"en": ["Berlin, Germany", "Land Berlin"], "ru": ["Berlin"]}
    assert len(entity.statements) == 0
    assert entity.sitelinks is None


def test_parse_q17948861():
    """Test parsing entity with references from real test data"""
    with open(TEST_DATA_DIR / "entities/Q17948861.json") as f:
        entity_json = json.load(f)

    entity = parse_entity(entity_json)
    assert entity.id == "Q17948861"
    assert entity.type == "item"
    assert len(entity.statements) > 0

    has_references = any(len(stmt.references) > 0 for stmt in entity.statements)
    assert has_references, "Entity should have at least one statement with references"


def test_parse_q3_sitelinks():
    """Test parsing entity with sitelinks without badges"""
    with open(TEST_DATA_DIR / "entities/Q3.json") as f:
        entity_json = json.load(f)

    entity = parse_entity(entity_json)
    assert entity.id == "Q3"
    assert entity.type == "item"
    assert entity.sitelinks is not None
    assert "enwiki" in entity.sitelinks
    assert entity.sitelinks["enwiki"]["site"] == "enwiki"
    assert entity.sitelinks["enwiki"]["title"] == "San Francisco"
    assert entity.sitelinks["enwiki"]["badges"] == []
    assert "ruwiki" in entity.sitelinks
    assert entity.sitelinks["ruwiki"]["title"] == "Сан Франциско"


def test_parse_q5_sitelinks_with_badges():
    """Test parsing entity with sitelinks containing badges"""
    with open(TEST_DATA_DIR / "entities/Q5.json") as f:
        entity_json = json.load(f)

    entity = parse_entity(entity_json)
    assert entity.id == "Q5"
    assert entity.type == "item"
    assert entity.sitelinks is not None
    assert "enwiki" in entity.sitelinks
    assert entity.sitelinks["enwiki"]["badges"] == []
    assert "ruwiki" in entity.sitelinks
    assert entity.sitelinks["ruwiki"]["badges"] == ["Q666", "Q42"]


def test_parse_q4_complex_statements():
    """Test parsing entity with complex statements including novalue, somevalue, and deprecated rank"""
    with open(TEST_DATA_DIR / "entities/Q4.json") as f:
        entity_json = json.load(f)

    entity = parse_entity(entity_json)
    assert entity.id == "Q4"
    assert entity.type == "item"
    assert len(entity.statements) > 0

    p2_statements = [stmt for stmt in entity.statements if stmt.property == "P2"]
    assert len(p2_statements) == 2
    assert any(stmt.rank.value == "preferred" for stmt in p2_statements)

    p3_statements = [stmt for stmt in entity.statements if stmt.property == "P3"]
    assert len(p3_statements) == 1
    assert p3_statements[0].value.kind == "commons_media"

    p4_statements = [stmt for stmt in entity.statements if stmt.property == "P4"]
    assert len(p4_statements) == 1
    assert p4_statements[0].value.kind == "globe"

    p5_statements = [stmt for stmt in entity.statements if stmt.property == "P5"]
    assert len(p5_statements) == 1
    assert p5_statements[0].value.kind == "monolingual"

    p9_statements = [stmt for stmt in entity.statements if stmt.property == "P9"]
    assert len(p9_statements) == 1
    assert p9_statements[0].value.kind == "url"

    p10_statements = [stmt for stmt in entity.statements if stmt.property == "P10"]
    assert len(p10_statements) == 1
    assert p10_statements[0].value.kind == "geo_shape"

    p11_statements = [stmt for stmt in entity.statements if stmt.property == "P11"]
    assert len(p11_statements) == 1
    assert p11_statements[0].value.kind == "external_id"


def test_parse_q6_complex_qualifiers():
    """Test parsing entity with complex qualifiers including multiple qualifiers per property"""
    with open(TEST_DATA_DIR / "entities/Q6.json") as f:
        entity_json = json.load(f)

    entity = parse_entity(entity_json)
    assert entity.id == "Q6"
    assert entity.type == "item"

    p7_statements = [stmt for stmt in entity.statements if stmt.property == "P7"]
    assert len(p7_statements) == 1

    qualifiers = p7_statements[0].qualifiers
    assert len(qualifiers) == 9

    p2_qualifiers = [q for q in qualifiers if q.property == "P2"]
    assert len(p2_qualifiers) == 2
    assert all(q.value.kind == "entity" for q in p2_qualifiers)

    p3_qualifiers = [q for q in qualifiers if q.property == "P3"]
    assert len(p3_qualifiers) == 1

    p5_qualifiers = [q for q in qualifiers if q.property == "P5"]
    assert len(p5_qualifiers) == 2

    p9_qualifiers = [q for q in qualifiers if q.property == "P9"]
    assert len(p9_qualifiers) == 2


def test_parse_q7_complex_references():
    """Test parsing entity with complex references containing multiple snaks"""
    with open(TEST_DATA_DIR / "entities/Q7.json") as f:
        entity_json = json.load(f)

    entity = parse_entity(entity_json)
    assert entity.id == "Q7"
    assert entity.type == "item"

    p7_statements = [stmt for stmt in entity.statements if stmt.property == "P7"]
    assert len(p7_statements) == 1

    references = p7_statements[0].references
    assert len(references) == 1
    assert len(references[0].snaks) == 8

    reference = references[0]
    p2_snaks = [s for s in reference.snaks if s.property == "P2"]
    assert len(p2_snaks) == 2
    assert all(s.value.kind == "entity" for s in p2_snaks)

    p3_snaks = [s for s in reference.snaks if s.property == "P3"]
    assert len(p3_snaks) == 1

    p6_snaks = [s for s in reference.snaks if s.property == "P6"]
    assert len(p6_snaks) == 1
    assert p6_snaks[0].value.kind == "quantity"


def test_parse_q8_edge_case_dates():
    """Test parsing entity with edge case dates including invalid dates and different calendar models"""
    with open(TEST_DATA_DIR / "entities/Q8.json") as f:
        entity_json = json.load(f)

    entity = parse_entity(entity_json)
    assert entity.id == "Q8"
    assert entity.type == "item"

    p8_statements = [stmt for stmt in entity.statements if stmt.property == "P8"]
    assert len(p8_statements) >= 1

    first_statement = p8_statements[0]
    assert first_statement.value.kind == "time"
    assert first_statement.value.value == "-0200-00-00T00:00:00Z"
    assert first_statement.value.precision == 9

    has_timezone = any(stmt.value.timezone != 0 for stmt in p8_statements)
    assert has_timezone, "At least one statement should have non-zero timezone"


def test_parse_q9_duplicate_references():
    """Test parsing entity with multiple statements having identical references"""
    with open(TEST_DATA_DIR / "entities/Q9.json") as f:
        entity_json = json.load(f)

    entity = parse_entity(entity_json)
    assert entity.id == "Q9"
    assert entity.type == "item"

    p7_statements = [stmt for stmt in entity.statements if stmt.property == "P7"]
    assert len(p7_statements) == 2

    for stmt in p7_statements:
        assert len(stmt.references) == 1
        assert len(stmt.references[0].snaks) == 8


def test_parse_q10_simple():
    """Test parsing simple entity with single statement and preferred rank"""
    with open(TEST_DATA_DIR / "entities/Q10.json") as f:
        entity_json = json.load(f)

    entity = parse_entity(entity_json)
    assert entity.id == "Q10"
    assert entity.type == "item"

    assert len(entity.statements) == 1
    assert entity.statements[0].property == "P2"
    assert entity.statements[0].rank.value == "preferred"


def test_parse_q120248304():
    """Test parsing another real Wikidata entity"""
    with open(TEST_DATA_DIR / "entities/Q120248304.json") as f:
        entity_json = json.load(f)

    entity = parse_entity(entity_json)
    assert entity.id == "Q120248304"
    assert entity.type == "item"
    assert len(entity.statements) > 0


def test_parse_statement_with_qualifiers():
    """Test parsing statement with qualifiers"""
    statement_json = {
        "mainsnak": {
            "snaktype": "value",
            "property": "P6",
            "datatype": "wikibase-item",
            "datavalue": {
                "value": {"entity-type": "item", "numeric-id": 666, "id": "Q666"},
                "type": "wikibase-entityid"
            }
        },
        "type": "statement",
        "id": "Q6-$123",
        "rank": "preferred",
        "qualifiers": {
            "P2": [
                {
                    "snaktype": "value",
                    "property": "P2",
                    "datatype": "wikibase-item",
                    "datavalue": {
                        "value": {"entity-type": "item", "numeric-id": 42, "id": "Q42"},
                        "type": "wikibase-entityid"
                    }
                }
            ]
        },
        "references": []
    }

    statement = parse_statement(statement_json)
    assert len(statement.qualifiers) == 1
    assert statement.qualifiers[0].property == "P2"
    assert statement.qualifiers[0].value.kind == "entity"


def test_parse_statement_with_references():
    """Test parsing statement with references"""
    statement_json = {
        "mainsnak": {
            "snaktype": "value",
            "property": "P7",
            "datatype": "string",
            "datavalue": {
                "value": "test",
                "type": "string"
            }
        },
        "type": "statement",
        "id": "Q7-$123",
        "rank": "normal",
        "qualifiers": {},
        "references": [
            {
                "hash": "d2412760c57cacd8c8f24d9afde3b20c87161cca",
                "snaks": {
                    "P2": [
                        {
                            "snaktype": "value",
                            "property": "P2",
                            "datatype": "wikibase-item",
                            "datavalue": {
                                "value": {"entity-type": "item", "numeric-id": 42, "id": "Q42"},
                                "type": "wikibase-entityid"
                            }
                        }
                    ]
                }
            }
        ]
    }

    statement = parse_statement(statement_json)
    assert len(statement.references) == 1
    assert statement.references[0].hash == "d2412760c57cacd8c8f24d9afde3b20c87161cca"
    assert len(statement.references[0].snaks) == 1


def test_parse_entity_with_sitelinks():
    """Test parsing entity with sitelinks"""
    entity_json = {
        "id": "Q3",
        "type": "item",
        "labels": {
            "en": {"language": "en", "value": "Test"}
        },
        "descriptions": {},
        "aliases": {},
        "claims": {},
        "sitelinks": {
            "enwiki": {
                "site": "enwiki",
                "title": "Test",
                "badges": []
            }
        }
    }

    entity = parse_entity(entity_json)
    assert entity.sitelinks is not None
    assert "enwiki" in entity.sitelinks
    assert entity.sitelinks["enwiki"]["site"] == "enwiki"


def test_parse_value_with_novalue_snaktype():
    """Test that novalue snaktype raises ValueError"""
    snak_json = {
        "snaktype": "novalue",
        "property": "P1",
        "datatype": "wikibase-item",
        "datavalue": {
            "value": None,
            "type": "somevalue"
        }
    }

    with pytest.raises(ValueError, match="Only value snaks are supported"):
        parse_value(snak_json)


def test_parse_unsupported_datatype():
    """Test that unsupported datatype raises ValueError"""
    snak_json = {
        "snaktype": "value",
        "property": "P1",
        "datatype": "unknown-type",
        "datavalue": {
            "value": "test",
            "type": "string"
        }
    }

    with pytest.raises(ValueError, match="Unsupported value type"):
        parse_value(snak_json)
