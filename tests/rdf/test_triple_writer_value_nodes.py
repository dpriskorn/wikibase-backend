from models.internal_representation.values.time_value import TimeValue
from models.internal_representation.values.quantity_value import QuantityValue
from models.internal_representation.values.entity_value import EntityValue
from models.rdf_builder.writers.triple import TripleWriters


def test_needs_value_node_time():
    """Test that time values require value nodes"""
    time_val = TimeValue(
        value="+1964-05-15T00:00:00Z",
        precision=11,
        timezone=0,
        calendarmodel="http://www.wikidata.org/entity/Q1985727",
    )
    assert TripleWriters._needs_value_node(time_val) is True


def test_needs_value_node_quantity():
    """Test that quantity values require value nodes"""
    quantity_val = QuantityValue(value="+3", unit="http://www.wikidata.org/entity/Q199")
    assert TripleWriters._needs_value_node(quantity_val) is True


def test_needs_value_node_entity():
    """Test that entity values do not require value nodes"""
    entity_val = EntityValue(value="Q42")
    assert TripleWriters._needs_value_node(entity_val) is False


def test_needs_value_node_object_without_kind():
    """Test that objects without kind attribute return False"""
    obj = {"value": "test"}
    assert TripleWriters._needs_value_node(obj) is False
