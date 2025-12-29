import pytest

from services.shared.parsers import parse_value


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


def test_parse_novalue_value():
    """Test parsing novalue snaktype"""
    snak_json = {
        "snaktype": "novalue",
        "property": "P1"
    }

    value = parse_value(snak_json)
    assert value.kind == "novalue"
    assert value.value is None
    assert value.datatype_uri == "http://wikiba.se/ontology#NoValue"


def test_parse_somevalue_value():
    """Test parsing somevalue snaktype"""
    snak_json = {
        "snaktype": "somevalue",
        "property": "P1"
    }

    value = parse_value(snak_json)
    assert value.kind == "somevalue"
    assert value.value is None
    assert value.datatype_uri == "http://wikiba.se/ontology#SomeValue"


def test_parse_value_with_novalue_snaktype():
    """Test parsing novalue snaktype successfully"""
    snak_json = {
        "snaktype": "novalue",
        "property": "P1"
    }

    value = parse_value(snak_json)
    assert value.kind == "novalue"
    assert value.value is None
    assert value.datatype_uri == "http://wikiba.se/ontology#NoValue"


def test_parse_unsupported_datatype():
    """Test that unsupported datatype raises ValueError"""
    snak_json = {
        "snaktype": "value",
        "property": "P1",
        "datatype": "unknown-type",
        "datavalue": {
            "value": "test",
            "type": "another-unknown-type"
        }
    }

    with pytest.raises(ValueError, match="Unsupported value type"):
        parse_value(snak_json)
