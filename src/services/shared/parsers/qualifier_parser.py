from typing import Any

from .value_parser import parse_value
from ..models.internal_representation.qualifiers import Qualifier


def parse_qualifiers(qualifiers_json: dict[str, list[dict[str, Any]]]) -> list[Qualifier]:
    qualifiers = []

    for property_id, qualifier_list in qualifiers_json.items():
        for qualifier_json in qualifier_list:
            qualifier = Qualifier(
                property=qualifier_json.get("property", property_id),
                value=parse_value(qualifier_json)
            )
            qualifiers.append(qualifier)

    return qualifiers
