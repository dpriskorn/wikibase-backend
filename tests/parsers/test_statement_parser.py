import pytest

from services.shared.parsers import parse_statement


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


def test_parse_statement_with_novalue_mainsnak():
    """Test parsing statement with novalue mainsnak"""
    statement_json = {
        "mainsnak": {
            "snaktype": "novalue",
            "property": "P3"
        },
        "type": "statement",
        "id": "TEST-novalue",
        "rank": "normal",
        "qualifiers": {},
        "references": []
    }

    statement = parse_statement(statement_json)
    assert statement.property == "P3"
    assert statement.value.kind == "novalue"
    assert statement.value is not None


def test_parse_statement_with_somevalue_mainsnak():
    """Test parsing statement with somevalue mainsnak"""
    statement_json = {
        "mainsnak": {
            "snaktype": "somevalue",
            "property": "P5"
        },
        "type": "statement",
        "id": "TEST-somevalue",
        "rank": "normal",
        "qualifiers": {},
        "references": []
    }

    statement = parse_statement(statement_json)
    assert statement.property == "P5"
    assert statement.value.kind == "somevalue"
    assert statement.value is not None
