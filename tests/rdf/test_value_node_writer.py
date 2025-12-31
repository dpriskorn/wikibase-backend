from io import StringIO

from models.rdf_builder.writers.value_node import ValueNodeWriter
from models.internal_representation.values.time_value import TimeValue
from models.internal_representation.values.quantity_value import QuantityValue
from models.internal_representation.values.globe_value import GlobeValue


def test_write_time_value_node():
    """Test writing time value node"""
    time_val = TimeValue(
        value="+1964-05-15T00:00:00Z",
        precision=11,
        timezone=0,
        calendarmodel="http://www.wikidata.org/entity/Q1985727"
    )

    output = StringIO()
    ValueNodeWriter.write_time_value_node(output, "cd6dd2e48a93286891b0753a1110ac0a", time_val)

    result = output.getvalue()

    assert 'wdv:cd6dd2e48a93286891b0753a1110ac0a a wikibase:TimeValue' in result
    assert 'wikibase:timeValue "+1964-05-15T00:00:00Z"^^xsd:dateTime' in result
    assert 'wikibase:timePrecision "11"^^xsd:integer' in result
    assert 'wikibase:timeTimezone "0"^^xsd:integer' in result
    assert 'wikibase:timeCalendarModel <http://www.wikidata.org/entity/Q1985727>' in result


def test_write_quantity_value_node():
    """Test writing quantity value node"""
    quantity_val = QuantityValue(
        value="+3",
        unit="http://www.wikidata.org/entity/Q199"
    )

    output = StringIO()
    ValueNodeWriter.write_quantity_value_node(output, "26735f5641071ce58303f506fe005a54", quantity_val)

    result = output.getvalue()

    assert 'wdv:26735f5641071ce58303f506fe005a54 a wikibase:QuantityValue' in result
    assert 'wikibase:quantityAmount "+3"^^xsd:decimal' in result
    assert 'wikibase:quantityUnit <http://www.wikidata.org/entity/Q199>' in result


def test_write_globe_value_node():
    """Test writing globe coordinate value node"""
    globe_val = GlobeValue(
        value="Point(1.88108 50.94636)",
        latitude=50.94636,
        longitude=1.88108,
        precision=0.00001,
        globe="http://www.wikidata.org/entity/Q2"
    )

    output = StringIO()
    ValueNodeWriter.write_globe_value_node(output, "test123", globe_val)

    result = output.getvalue()

    assert 'wdv:test123 a wikibase:GlobecoordinateValue' in result
    assert 'wikibase:geoLatitude "50.94636"^^xsd:double' in result
    assert 'wikibase:geoLongitude "1.88108"^^xsd:double' in result
    assert 'wikibase:geoPrecision "1e-05"^^xsd:double' in result
    assert 'wikibase:geoGlobe <http://www.wikidata.org/entity/Q2>' in result
