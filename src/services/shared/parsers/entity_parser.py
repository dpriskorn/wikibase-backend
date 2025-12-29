from typing import Any

from services.shared.parsers.statement_parser import parse_statement
from services.shared.models.internal_representation.entity import Entity


def parse_entity(entity_json: dict[str, Any]) -> Entity:
    entity_id = entity_json.get("id", "")
    entity_type = entity_json.get("type", "item")

    labels_json = entity_json.get("labels", {})
    descriptions_json = entity_json.get("descriptions", {})
    aliases_json = entity_json.get("aliases", {})
    claims_json = entity_json.get("claims", {})
    sitelinks_json = entity_json.get("sitelinks", {})

    labels = _parse_labels(labels_json)
    descriptions = _parse_descriptions(descriptions_json)
    aliases = _parse_aliases(aliases_json)
    statements = _parse_statements(claims_json)

    return Entity(
        id=entity_id,
        type=entity_type,
        labels=labels,
        descriptions=descriptions,
        aliases=aliases,
        statements=statements,
        sitelinks=sitelinks_json if sitelinks_json else None
    )


def _parse_labels(labels_json: dict[str, dict[str, str]]) -> dict[str, str]:
    return {lang: label_data.get("value", "") for lang, label_data in labels_json.items()}


def _parse_descriptions(descriptions_json: dict[str, dict[str, str]]) -> dict[str, str]:
    return {lang: desc_data.get("value", "") for lang, desc_data in descriptions_json.items()}


def _parse_aliases(aliases_json: dict[str, list[dict[str, str]]]) -> dict[str, list[str]]:
    return {lang: [alias_data.get("value", "") for alias_data in alias_list] for lang, alias_list in aliases_json.items()}


def _parse_statements(claims_json: dict[str, list[dict[str, Any]]]) -> list:
    statements = []
    for property_id, claim_list in claims_json.items():
        for claim_json in claim_list:
            try:
                statement = parse_statement(claim_json)
                statements.append(statement)
            except ValueError:
                continue
    return statements
