import pytest
from models.rdf_builder.value_node import generate_value_node_uri, _serialize_value
from models.internal_representation.values.time_value import TimeValue
from models.internal_representation.values.quantity_value import QuantityValue
from models.internal_representation.values.globe_value import GlobeValue


def test_serialize_time_value():
    """Test serialization of time values"""
    value = TimeValue(
        value="+1964-05-15T00:00:00Z",
        precision=11,
        timezone=0,
        calendarmodel="http://www.wikidata.org/entity/Q1985727"
    )
    serialized = _serialize_value(value)
    expected = "t:+1964-05-15T00:00:00Z:11:0:http://www.wikidata.org/entity/Q1985727"
    assert serialized == expected


def test_serialize_quantity_value():
    """Test serialization of quantity values"""
    value = QuantityValue(
        value="+3",
        unit="http://www.wikidata.org/entity/Q199"
    )
    serialized = _serialize_value(value)
    expected = "q:+3:http://www.wikidata.org/entity/Q199"
    assert serialized == expected


def test_serialize_quantity_with_bounds():
    """Test serialization of quantity values with bounds"""
    value = QuantityValue(
        value="+5",
        unit="http://www.wikidata.org/entity/Q11573",
        upper_bound="+5.5",
        lower_bound="+4.5"
    )
    serialized = _serialize_value(value)
    expected = "q:+5:http://www.wikidata.org/entity/Q11573:+5.5:+4.5"
    assert serialized == expected


def test_serialize_globe_value():
    """Test serialization of globe coordinates"""
    value = GlobeValue(
        value="Point(1.88108 50.94636)",
        latitude=50.94636,
        longitude=1.88108,
        precision=0.00001,
        globe="http://www.wikidata.org/entity/Q2"
    )
    serialized = _serialize_value(value)
    expected = "g:50.94636:1.88108:1e-05:http://www.wikidata.org/entity/Q2"
    assert serialized == expected


def test_generate_value_node_uri_time():
    """Test value node URI generation for time"""
    value = TimeValue(
        value="+1964-05-15T00:00:00Z",
        precision=11,
        timezone=0,
        calendarmodel="http://www.wikidata.org/entity/Q1985727"
    )
    uri = generate_value_node_uri(value, "P569")
    assert len(uri) == 32  # MD5 hash length
    assert uri.isalnum()


def test_generate_value_node_uri_quantity():
    """Test value node URI generation for quantity"""
    value = QuantityValue(
        value="+3",
        unit="http://www.wikidata.org/entity/Q199"
    )
    uri = generate_value_node_uri(value, "P1971")
    assert len(uri) == 32
    assert uri.isalnum()


def test_generate_value_node_uri_consistency():
    """Test that identical values produce identical URIs"""
    value = TimeValue(
        value="+1964-05-15T00:00:00Z",
        precision=11,
        timezone=0,
        calendarmodel="http://www.wikidata.org/entity/Q1985727"
    )
    uri1 = generate_value_node_uri(value, "P569")
    uri2 = generate_value_node_uri(value, "P569")
    assert uri1 == uri2


def test_generate_value_node_uri_different_properties():
    """Test that same value with different properties produces different URIs"""
    value = TimeValue(
        value="+1964-05-15T00:00:00Z",
        precision=11,
        timezone=0,
        calendarmodel="http://www.wikidata.org/entity/Q1985727"
    )
    uri1 = generate_value_node_uri(value, "P569")
    uri2 = generate_value_node_uri(value, "P580")
    assert uri1 != uri2
