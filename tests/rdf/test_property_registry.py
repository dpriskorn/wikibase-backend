import json
from pathlib import Path
import pytest

from models.rdf_builder.property_registry.models import (
    PropertyShape,
    PropertyPredicates,
)
from models.rdf_builder.property_registry.registry import PropertyRegistry
from models.rdf_builder.property_registry.loader import load_property_registry
from models.rdf_builder.ontology.datatypes import property_shape


def test_property_shape_with_labels_and_descriptions():
    labels = {"en": {"language": "en", "value": "instance of"}}
    descriptions = {
        "en": {"language": "en", "value": "type to which this subject corresponds"}
    }

    shape = PropertyShape(
        pid="P31",
        datatype="wikibase-item",
        predicates=PropertyPredicates(
            direct="wdt:P31", statement="ps:P31", qualifier="pq:P31", reference="pr:P31"
        ),
        labels=labels,
        descriptions=descriptions,
    )

    assert shape.pid == "P31"
    assert shape.datatype == "wikibase-item"
    assert shape.labels == labels
    assert shape.descriptions == descriptions
    assert shape.predicates.direct == "wdt:P31"


def test_property_shape_empty_labels_descriptions():
    shape = PropertyShape(
        pid="P17",
        datatype="wikibase-item",
        predicates=PropertyPredicates(
            direct="wdt:P17", statement="ps:P17", qualifier="pq:P17", reference="pr:P17"
        ),
    )

    assert shape.labels == {}
    assert shape.descriptions == {}


def test_property_shape_factory_with_labels_descriptions():
    labels = {"en": {"language": "en", "value": "instance of"}}
    descriptions = {
        "en": {"language": "en", "value": "type to which this subject corresponds"}
    }

    shape = property_shape(
        "P31", "wikibase-item", labels=labels, descriptions=descriptions
    )

    assert shape.pid == "P31"
    assert shape.datatype == "wikibase-item"
    assert shape.labels == labels
    assert shape.descriptions == descriptions
    assert shape.predicates.direct == "wdt:P31"


def test_property_shape_factory_without_labels_descriptions():
    shape = property_shape("P31", "wikibase-item")

    assert shape.labels == {}
    assert shape.descriptions == {}


def test_property_shape_factory_time_datatype_with_metadata():
    labels = {"en": {"language": "en", "value": "point in time"}}
    descriptions = {
        "en": {"language": "en", "value": "time and date something took place"}
    }

    shape = property_shape("P585", "time", labels=labels, descriptions=descriptions)

    assert shape.pid == "P585"
    assert shape.datatype == "time"
    assert shape.labels == labels
    assert shape.descriptions == descriptions
    assert shape.predicates.value_node == "psv:P585"


def test_property_registry_shape_method():
    properties = {
        "P31": property_shape(
            "P31",
            "wikibase-item",
            labels={"en": {"language": "en", "value": "instance of"}},
        ),
        "P17": property_shape("P17", "wikibase-item"),
    }
    registry = PropertyRegistry(properties=properties)

    shape = registry.shape("P31")
    assert shape.pid == "P31"
    assert shape.labels == {"en": {"language": "en", "value": "instance of"}}


def test_property_registry_shape_not_found():
    registry = PropertyRegistry(properties={})

    with pytest.raises(KeyError) as exc:
        registry.shape("P999")

    assert "Property P999 not in registry" in str(exc.value)


def test_loader_with_json_and_csv(tmp_path: Path):
    csv_content = "property_id,datatype\nP31,wikibase-item\nP17,wikibase-item\n"
    csv_path = tmp_path / "properties.csv"
    csv_path.write_text(csv_content)

    p31_json = {
        "id": "P31",
        "labels": {"en": {"language": "en", "value": "instance of"}},
        "descriptions": {
            "en": {"language": "en", "value": "type to which this subject corresponds"}
        },
    }
    p31_path = tmp_path / "P31.json"
    p31_path.write_text(json.dumps(p31_json))

    p17_json = {
        "id": "P17",
        "labels": {"en": {"language": "en", "value": "country"}},
        "descriptions": {},
    }
    p17_path = tmp_path / "P17.json"
    p17_path.write_text(json.dumps(p17_json))

    registry = load_property_registry(tmp_path)

    p31_shape = registry.shape("P31")
    assert p31_shape.pid == "P31"
    assert p31_shape.datatype == "wikibase-item"
    assert p31_shape.labels["en"]["value"] == "instance of"
    assert (
        p31_shape.descriptions["en"]["value"]
        == "type to which this subject corresponds"
    )

    p17_shape = registry.shape("P17")
    assert p17_shape.pid == "P17"
    assert p17_shape.datatype == "wikibase-item"
    assert p17_shape.labels["en"]["value"] == "country"
    assert p17_shape.descriptions == {}


def test_loader_without_csv_fallback_to_string(tmp_path: Path):
    p31_json = {
        "id": "P31",
        "labels": {"en": {"language": "en", "value": "instance of"}},
    }
    p31_path = tmp_path / "P31.json"
    p31_path.write_text(json.dumps(p31_json))

    registry = load_property_registry(tmp_path)

    shape = registry.shape("P31")
    assert shape.datatype == "string"


def test_loader_empty_labels_descriptions(tmp_path: Path):
    csv_content = "property_id,datatype\nP31,wikibase-item\n"
    csv_path = tmp_path / "properties.csv"
    csv_path.write_text(csv_content)

    p31_json = {"id": "P31"}
    p31_path = tmp_path / "P31.json"
    p31_path.write_text(json.dumps(p31_json))

    registry = load_property_registry(tmp_path)

    shape = registry.shape("P31")
    assert shape.labels == {}
    assert shape.descriptions == {}
