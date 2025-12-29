from typing import Any

from services.shared.parsers.value_parser import parse_value
from services.shared.models.internal_representation.references import Reference, ReferenceValue
from services.shared.models.internal_representation.json_fields import JsonField


def parse_reference(reference_json: dict[str, Any]) -> Reference:
    reference_hash = reference_json.get(JsonField.HASH.value, "")
    snaks_json = reference_json.get(JsonField.SNAKS.value, {})

    snaks = []
    for property_id, snak_list in snaks_json.items():
        for snak_json in snak_list:
            snak = ReferenceValue(
                property=snak_json.get(JsonField.PROPERTY.value, property_id),
                value=parse_value(snak_json)
            )
            snaks.append(snak)

    return Reference(
        hash=reference_hash,
        snaks=snaks
    )


def parse_references(references_json: list[dict[str, Any]]) -> list[Reference]:
    references = []

    for reference_json in references_json:
        reference_hash = reference_json.get(JsonField.HASH.value, "")
        snaks_json = reference_json.get(JsonField.SNAKS.value, {})

        snaks = []
        for property_id, snak_list in snaks_json.items():
            for snak_json in snak_list:
                snak = ReferenceValue(
                    property=snak_json.get(JsonField.PROPERTY.value, property_id),
                    value=parse_value(snak_json)
                )
                snaks.append(snak)

        reference = Reference(
            hash=reference_hash,
            snaks=snaks
        )
        references.append(reference)

    return references
