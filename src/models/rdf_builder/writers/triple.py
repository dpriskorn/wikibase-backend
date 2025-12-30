from typing import TextIO, Any

from models.rdf_builder.uri_generator import URIGenerator
from models.rdf_builder.property_registry.models import PropertyShape
from models.rdf_builder.value_formatters import ValueFormatter


class TripleWriters:
    uri = URIGenerator()

    @staticmethod
    def write_header(output: TextIO):
        from models.rdf_builder.writers.prefixes import TURTLE_PREFIXES
        output.write(TURTLE_PREFIXES)

    @staticmethod
    def write_entity_type(output: TextIO, entity_id: str):
        output.write(
            f'{TripleWriters.uri.entity_prefixed(entity_id)} a wikibase:Item .\n'
        )

    @staticmethod
    def write_dataset_triples(output: TextIO, entity_id: str):
        data_uri = TripleWriters.uri.data_prefixed(entity_id)
        entity_uri = TripleWriters.uri.entity_prefixed(entity_id)

        output.write(f'{data_uri} a schema:Dataset .\n')
        output.write(f'{data_uri} schema:about {entity_uri} .\n')
        output.write(
            f'{data_uri} cc:license '
            '<http://creativecommons.org/publicdomain/zero/1.0/> .\n'
        )

    @staticmethod
    def write_label(output: TextIO, entity_id: str, lang: str, label: str):
        entity_uri = TripleWriters.uri.entity_prefixed(entity_id)
        output.write(f'{entity_uri} rdfs:label "{label}"@{lang} .\n')

    @staticmethod
    def write_description(output: TextIO, entity_id: str, lang: str, description: str):
        entity_uri = TripleWriters.uri.entity_prefixed(entity_id)
        output.write(f'{entity_uri} schema:description "{description}"@{lang} .\n')

    @staticmethod
    def write_alias(output: TextIO, entity_id: str, lang: str, alias: str):
        entity_uri = TripleWriters.uri.entity_prefixed(entity_id)
        output.write(f'{entity_uri} skos:altLabel "{alias}"@{lang} .\n')

    @staticmethod
    def write_sitelink(output: TextIO, entity_id: str, sitelink_data: dict):
        entity_uri = TripleWriters.uri.entity_prefixed(entity_id)
        site_key = sitelink_data.get("site", "")
        title = sitelink_data.get("title", "")
        wiki_url = f"https://{site_key}.wikipedia.org/wiki/{title.replace(' ', '_')}"
        output.write(f'{entity_uri} schema:sameAs <{wiki_url}> .\n')

    @staticmethod
    def write_statement(
        output: TextIO,
        entity_id: str,
        statement: Any,
        shape: PropertyShape,
    ):
        from models.internal_representation.ranks import Rank

        entity_uri = TripleWriters.uri.entity_prefixed(entity_id)
        stmt_uri = TripleWriters.uri.statement_prefixed(statement.statement_id)

        # Link entity → statement
        output.write(
            f'{entity_uri} p:{statement.property} {stmt_uri} .\n'
        )

        output.write(f'{stmt_uri} a wikibase:Statement .\n')

        # Statement value
        value = ValueFormatter.format_value(statement.value)
        output.write(
            f'<{stmt_uri}> {shape.predicates.statement} {value} .\n'
        )

        # Rank
        rank = (
            "NormalRank" if statement.rank == Rank.NORMAL else
            "PreferredRank" if statement.rank == Rank.PREFERRED else
            "DeprecatedRank"
        )
        output.write(
            f'<{stmt_uri}> wikibase:rank wikibase:{rank} .\n'
        )

        # Qualifiers
        for qual in statement.qualifiers:
            qv = ValueFormatter.format_value(qual.value)
            output.write(
                f'<{stmt_uri}> {shape.predicates.qualifier} {qv} .\n'
            )

        # References
        for idx, ref in enumerate(statement.references):
            ref_uri = TripleWriters.uri.reference_uri(stmt_uri, idx)
            output.write(
                f'<{stmt_uri}> prov:wasDerivedFrom <{ref_uri}> .\n'
            )

            for snak in ref.snaks:
                rv = ValueFormatter.format_value(snak.value)
                output.write(
                    f'<{ref_uri}> {shape.predicates.reference} {rv} .\n'
                )
