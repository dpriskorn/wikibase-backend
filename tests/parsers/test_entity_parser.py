import json
import pytest

from models.json_parser import parse_entity
from parsers.conftest import TEST_DATA_JSON_DIR


def test_parse_entity_basic():
    """Test parsing basic entity"""
    entity_json = {
        "id": "Q42",
        "type": "item",
        "labels": {"en": {"language": "en", "value": "Douglas Adams"}},
        "descriptions": {"en": {"language": "en", "value": "English author"}},
        "aliases": {"en": [{"language": "en", "value": "DA"}]},
        "claims": {},
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
    with open(TEST_DATA_JSON_DIR / "entities/Q1.json") as f:
        entity_json = json.load(f)

    entity = parse_entity(entity_json)

    assert entity.id == "Q1"
    assert entity.type == "item"
    assert len(entity.labels) > 0  # Q1 now has labels
    assert len(entity.descriptions) > 0  # Q1 now has descriptions
    assert len(entity.aliases) > 0  # Q1 now has aliases
    assert len(entity.statements) > 0  # Q1 now has statements
    assert entity.sitelinks is not None  # Q1 now has sitelinks


def test_parse_q42():
    """Test parsing Douglas Adams entity from real test data - uses wrapper format"""
    with open(TEST_DATA_JSON_DIR / "entities/Q42.json") as f:
        data = json.load(f)

    entity_json = data["entities"]["Q42"]
    entity = parse_entity(entity_json)
    assert entity.id == "Q42"
    assert entity.type == "item"
    assert len(entity.labels) > 0
    assert len(entity.statements) > 0


def test_parse_q42_detailed():
    """Test parsing Q42 with detailed verification of content - uses wrapper format"""
    with open(TEST_DATA_JSON_DIR / "entities/Q42.json") as f:
        data = json.load(f)

    entity_json = data["entities"]["Q42"]
    entity = parse_entity(entity_json)
    assert entity.id == "Q42"
    assert entity.type == "item"

    assert len(entity.labels) > 50
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
    """Test parsing P2.json"""
    p2_path = TEST_DATA_JSON_DIR / "entities/P2.json"

    if not p2_path.exists():
        pytest.skip("P2.json not found in test data")

    with open(p2_path) as f:
        entity_json = json.load(f)

    entity = parse_entity(entity_json)

    assert entity.id == "P2"
    assert entity.type == "item"
    assert entity.labels == {
        "ab": "акосмос",
        "af": "heelal",
        "am": "ጠፈር",
    }
    assert entity.aliases == {
        "en": ["Berlin, Germany", "Land Berlin"],
        "ru": ["Berlin"],
    }
    assert len(entity.statements) == 0
    assert entity.sitelinks is None


def test_parse_q17948861():
    """Test parsing entity with references from real test data - uses wrapper format"""
    with open(TEST_DATA_JSON_DIR / "entities/Q17948861.json") as f:
        data = json.load(f)

    entity_json = data["entities"]["Q17948861"]
    entity = parse_entity(entity_json)
    assert entity.id == "Q17948861"
    assert entity.type == "item"
    assert len(entity.statements) > 0


def test_parse_q3_sitelinks():
    """Test parsing entity with sitelinks without badges"""
    with open(TEST_DATA_JSON_DIR / "entities/Q3.json") as f:
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
    with open(TEST_DATA_JSON_DIR / "entities/Q5.json") as f:
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
    with open(TEST_DATA_JSON_DIR / "entities/Q4.json") as f:
        entity_json = json.load(f)

    entity = parse_entity(entity_json)
    assert entity.id == "Q4"
    assert entity.type == "item"
    assert len(entity.statements) > 0

    p2_statements = [stmt for stmt in entity.statements if stmt.property == "P2"]
    assert len(p2_statements) == 2
    assert any(stmt.rank.value == "preferred" for stmt in p2_statements)

    p3_statements = [stmt for stmt in entity.statements if stmt.property == "P3"]
    assert len(p3_statements) == 2
    assert p3_statements[0].value.kind == "commons_media"

    p4_statements = [stmt for stmt in entity.statements if stmt.property == "P4"]
    assert len(p4_statements) == 1
    assert p4_statements[0].value.kind == "globe"

    p5_statements = [stmt for stmt in entity.statements if stmt.property == "P5"]
    assert len(p5_statements) == 3
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
    with open(TEST_DATA_JSON_DIR / "entities/Q6.json") as f:
        entity_json = json.load(f)

    entity = parse_entity(entity_json)
    assert entity.id == "Q6"
    assert entity.type == "item"

    p7_statements = [stmt for stmt in entity.statements if stmt.property == "P7"]
    assert len(p7_statements) == 1

    qualifiers = p7_statements[0].qualifiers
    assert len(qualifiers) == 13

    p2_qualifiers = [q for q in qualifiers if q.property == "P2"]
    assert len(p2_qualifiers) == 2
    assert all(q.value.kind == "entity" for q in p2_qualifiers)

    p3_qualifiers = [q for q in qualifiers if q.property == "P3"]
    assert len(p3_qualifiers) == 2

    p5_qualifiers = [q for q in qualifiers if q.property == "P5"]
    assert len(p5_qualifiers) == 3

    p9_qualifiers = [q for q in qualifiers if q.property == "P9"]
    assert len(p9_qualifiers) == 2


def test_parse_q10_simple():
    """Test parsing simple entity with single statement and preferred rank"""
    with open(TEST_DATA_JSON_DIR / "entities/Q10.json") as f:
        entity_json = json.load(f)

    entity = parse_entity(entity_json)
    assert entity.id == "Q10"
    assert entity.type == "item"

    assert len(entity.statements) == 1
    assert entity.statements[0].property == "P2"
    assert entity.statements[0].rank.value == "preferred"


def test_parse_q120248304():
    """Test parsing another real Wikidata entity"""
    with open(TEST_DATA_JSON_DIR / "entities/Q120248304.json") as f:
        data = json.load(f)

    entity_json = data["entities"]["Q120248304"]
    entity = parse_entity(entity_json)
    assert entity.id == "Q120248304"
    assert entity.type == "item"
    assert len(entity.statements) > 0


def test_parse_entity_with_sitelinks():
    """Test parsing entity with sitelinks"""
    entity_json = {
        "id": "Q3",
        "type": "item",
        "labels": {"en": {"language": "en", "value": "Test"}},
        "descriptions": {},
        "aliases": {},
        "claims": {},
        "sitelinks": {"enwiki": {"site": "enwiki", "title": "Test", "badges": []}},
    }

    entity = parse_entity(entity_json)
    assert entity.sitelinks is not None
    assert "enwiki" in entity.sitelinks
    assert entity.sitelinks["enwiki"]["site"] == "enwiki"
