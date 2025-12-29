from typing import Any

from services.shared.parsers.value_parser import parse_value
from services.shared.models.internal_representation.qualifiers import Qualifier
from services.shared.models.internal_representation.json_fields import JsonField


def parse_qualifier(qualifier_json: dict[str, Any], property_id: str = "") -> Qualifier:
    return Qualifier(
        property=qualifier_json.get(JsonField.PROPERTY.value, property_id),
        value=parse_value(qualifier_json)
    )


def parse_qualifiers(qualifiers_json: dict[str, list[dict[str, Any]]]) -> list[Qualifier]:
    qualifiers = []

    for property_id, qualifier_list in qualifiers_json.items():
        for qualifier_json in qualifier_list:
            qualifier = Qualifier(
                property=qualifier_json.get(JsonField.PROPERTY.value, property_id),
                value=parse_value(qualifier_json)
            )
            qualifiers.append(qualifier)

    return qualifiers
