import pytest

from services.shared.parsers import parse_qualifiers, parse_qualifier


def test_parse_qualifiers_basic():
    """Test parsing qualifiers with entity values"""
    qualifiers_json = {
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

    qualifiers = parse_qualifiers(qualifiers_json)
    assert len(qualifiers) == 1
    assert qualifiers[0].property == "P2"
    assert qualifiers[0].value.kind == "entity"
    assert qualifiers[0].value.value == "Q42"


def test_parse_qualifiers_multiple():
    """Test parsing qualifiers with multiple qualifiers of same property"""
    qualifiers_json = {
        "P2": [
            {
                "snaktype": "value",
                "property": "P2",
                "datatype": "wikibase-item",
                "datavalue": {
                    "value": {"entity-type": "item", "numeric-id": 42},
                    "type": "wikibase-entityid"
                }
            },
            {
                "snaktype": "value",
                "property": "P2",
                "datatype": "wikibase-item",
                "datavalue": {
                    "value": {"entity-type": "item", "numeric-id": 666},
                    "type": "wikibase-entityid"
                }
            }
        ]
    }

    qualifiers = parse_qualifiers(qualifiers_json)
    assert len(qualifiers) == 2
    assert all(q.property == "P2" for q in qualifiers)
    assert all(q.value.kind == "entity" for q in qualifiers)


def test_parse_qualifier_with_novalue():
    """Test parsing qualifier with novalue"""
    qualifier_json = {
        "snaktype": "novalue",
        "property": "P2"
    }

    qualifier = parse_qualifier(qualifier_json)
    assert qualifier.property == "P2"
    assert qualifier.value.kind == "novalue"


def test_parse_qualifier_with_somevalue():
    """Test parsing qualifier with somevalue"""
    qualifier_json = {
        "snaktype": "somevalue",
        "property": "P3"
    }

    qualifier = parse_qualifier(qualifier_json)
    assert qualifier.property == "P3"
    assert qualifier.value.kind == "somevalue"
