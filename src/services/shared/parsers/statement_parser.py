from typing import Any

from .value_parser import parse_value
from .qualifier_parser import parse_qualifiers
from .reference_parser import parse_references
from ..models.internal_representation.statements import Statement
from ..models.internal_representation.ranks import Rank


def parse_statement(statement_json: dict[str, Any]) -> Statement:
    mainsnak = statement_json.get("mainsnak", {})
    rank = statement_json.get("rank", "normal")
    qualifiers_json = statement_json.get("qualifiers", {})
    references_json = statement_json.get("references", [])
    statement_id = statement_json.get("id", "")

    return Statement(
        property=mainsnak.get("property", ""),
        value=parse_value(mainsnak),
        rank=Rank(rank),
        qualifiers=parse_qualifiers(qualifiers_json),
        references=parse_references(references_json),
        statement_id=statement_id
    )
