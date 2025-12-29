from typing import Any

from services.shared.parsers.value_parser import parse_value
from services.shared.parsers.qualifier_parser import parse_qualifiers
from services.shared.parsers.reference_parser import parse_references
from services.shared.models.internal_representation.statements import Statement


def parse_statement(statement_json: dict[str, Any]) -> Statement:
    mainsnak = statement_json.get("mainsnak", {})
    rank = statement_json.get("rank", "normal")
    qualifiers_json = statement_json.get("qualifiers", {})
    references_json = statement_json.get("references", [])
    statement_id = statement_json.get("id", "")

    return Statement(
        property=mainsnak.get("property", ""),
        value=parse_value(mainsnak),
        rank=rank,
        qualifiers=parse_qualifiers(qualifiers_json),
        references=parse_references(references_json),
        statement_id=statement_id
    )
