from io import StringIO

from models.rdf_builder.property_registry.models import (
    PropertyShape,
    PropertyPredicates,
)
from models.rdf_builder.property_registry.registry import PropertyRegistry
from models.rdf_builder.ontology.datatypes import property_shape
from models.rdf_builder.writers.property_ontology import PropertyOntologyWriter


def test_write_property_metadata_with_english_labels():
    labels = {"en": {"language": "en", "value": "instance of"}}
    descriptions = {
        "en": {"language": "en", "value": "type to which this subject corresponds"}
    }
    shape = property_shape(
        "P31", "wikibase-item", labels=labels, descriptions=descriptions
    )

    output = StringIO()
    PropertyOntologyWriter.write_property_metadata(output, shape)
    result = output.getvalue()

    assert "wd:P31 a wikibase:Property" in result
    assert 'rdfs:label "instance of"@en' in result
    assert 'skos:prefLabel "instance of"@en' in result
    assert 'schema:name "instance of"@en' in result
    assert 'schema:description "type to which this subject corresponds"@en' in result
    assert "wikibase:propertyType <http://wikiba.se/ontology#WikibaseItem>" in result
    assert "wikibase:directClaim wdt:P31" in result
    assert "wikibase:claim p:P31" in result
    assert "wikibase:statementProperty ps:P31" in result
    assert "wikibase:qualifier pq:P31" in result
    assert "wikibase:reference pr:P31" in result
    assert "wikibase:novalue wdno:P31" in result


def test_write_property_metadata_multiple_languages():
    labels = {
        "en": {"language": "en", "value": "instance of"},
        "de": {"language": "de", "value": "ist ein"},
    }
    descriptions = {
        "en": {"language": "en", "value": "type to which this subject corresponds"},
        "de": {"language": "de", "value": "Typ, dem dieses Subjekt entspricht"},
    }
    shape = property_shape(
        "P31", "wikibase-item", labels=labels, descriptions=descriptions
    )

    output = StringIO()
    PropertyOntologyWriter.write_property_metadata(output, shape)
    result = output.getvalue()

    assert 'rdfs:label "instance of"@en' in result
    assert 'rdfs:label "ist ein"@de' in result
    assert 'schema:description "type to which this subject corresponds"@en' in result
    assert 'schema:description "Typ, dem dieses Subjekt entspricht"@de' in result


def test_write_property_metadata_empty_labels_descriptions():
    shape = property_shape("P999", "string", labels={}, descriptions={})

    output = StringIO()
    PropertyOntologyWriter.write_property_metadata(output, shape)
    result = output.getvalue()

    assert "wd:P999 a wikibase:Property" in result
    assert "rdfs:label" not in result
    assert "schema:description" not in result
    assert "wikibase:propertyType" in result


def test_write_property_metadata_time_datatype():
    labels = {"en": {"language": "en", "value": "point in time"}}
    shape = property_shape("P585", "time", labels=labels, descriptions={})

    output = StringIO()
    PropertyOntologyWriter.write_property_metadata(output, shape)
    result = output.getvalue()

    assert "wikibase:statementValue psv:P585" in result
    assert "wikibase:qualifierValue pqv:P585" in result
    assert "wikibase:referenceValue prv:P585" in result


def test_write_property_metadata_without_value_node():
    labels = {"en": {"language": "en", "value": "instance of"}}
    shape = property_shape("P31", "wikibase-item", labels=labels, descriptions={})

    output = StringIO()
    PropertyOntologyWriter.write_property_metadata(output, shape)
    result = output.getvalue()

    assert "wikibase:statementValue" not in result
    assert "wikibase:qualifierValue" not in result
    assert "wikibase:referenceValue" not in result


def test_write_property_predicates_with_value_node():
    shape = property_shape("P585", "time", labels={}, descriptions={})

    output = StringIO()
    PropertyOntologyWriter.write_property(output, shape)
    result = output.getvalue()

    assert "p:P585 a owl:ObjectProperty" in result
    assert "psv:P585 a owl:ObjectProperty" in result
    assert "pqv:P585 a owl:ObjectProperty" in result
    assert "prv:P585 a owl:ObjectProperty" in result
    assert "wdt:P585 a owl:DatatypeProperty" in result
    assert "ps:P585 a owl:ObjectProperty" in result
    assert "pq:P585 a owl:ObjectProperty" in result
    assert "pr:P585 a owl:ObjectProperty" in result


def test_write_property_metadata_conditional():
    """Test that wikibase:statementValue is only written for properties with value nodes"""
    # wikibase-item (no value node predicate)
    shape = property_shape("P31", "wikibase-item", labels={}, descriptions={})
    output = StringIO()
    PropertyOntologyWriter.write_property_metadata(output, shape)
    result = output.getvalue()

    # All properties get wikibase:statementProperty
    assert "wikibase:statementProperty ps:P31" in result
    # But only properties with value nodes get wikibase:statementValue
    assert "wikibase:statementValue psv:P31" not in result

    # globe-coordinate (has value node predicate)
    shape2 = property_shape("P625", "globe-coordinate", labels={}, descriptions={})
    output2 = StringIO()
    PropertyOntologyWriter.write_property_metadata(output2, shape2)
    result2 = output2.getvalue()

    # Has wikibase:statementValue for value node properties
    assert "wikibase:statementValue psv:P625" in result2


def test_write_property_novalue_class():
    output = StringIO()
    PropertyOntologyWriter.write_novalue_class(output, "P31")
    result = output.getvalue()

    assert "wdno:P31 a owl:Class" in result
    assert "owl:complementOf" in result
    assert "owl:onProperty wdt:P31" in result
    assert "owl:someValuesFrom owl:Thing" in result
