from typing import Any

from .value_parser import parse_value
from ..models.internal_representation.references import Reference, ReferenceValue


def parse_references(references_json: list[dict[str, Any]]) -> list[Reference]:
    references = []

    for reference_json in references_json:
        reference_hash = reference_json.get("hash", "")
        snaks_json = reference_json.get("snaks", {})

        snaks = []
        for property_id, snak_list in snaks_json.items():
            for snak_json in snak_list:
                snak = ReferenceValue(
                    property=snak_json.get("property", property_id),
                    value=parse_value(snak_json)
                )
                snaks.append(snak)

        reference = Reference(
            hash=reference_hash,
            snaks=snaks
        )
        references.append(reference)

    return references
