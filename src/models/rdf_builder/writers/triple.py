import logging
from typing import TextIO

from models.rdf_builder.property_registry.models import PropertyShape
from models.rdf_builder.uri_generator import URIGenerator
from models.rdf_builder.value_formatters import ValueFormatter
from models.rdf_builder.value_node import generate_value_node_uri
from models.rdf_builder.writers.value_node import ValueNodeWriter
from models.rdf_builder.hashing.deduplication_cache import HashDedupeBag

logger = logging.getLogger(__name__)


class TripleWriters:
    uri = URIGenerator()

    @staticmethod
    def _needs_value_node(value) -> bool:
        """Check if value requires structured value node"""
        if hasattr(value, "kind"):
            return value.kind in ("time", "quantity", "globe")
        return False

    @staticmethod
    def write_header(output: TextIO):
        from models.rdf_builder.writers.prefixes import TURTLE_PREFIXES

        output.write(TURTLE_PREFIXES)

    @staticmethod
    def write_entity_type(output: TextIO, entity_id: str):
        output.write(
            f"{TripleWriters.uri.entity_prefixed(entity_id)} a wikibase:Item .\n"
        )

    @staticmethod
    def write_dataset_triples(output: TextIO, entity_id: str):
        data_uri = TripleWriters.uri.data_prefixed(entity_id)
        entity_uri = TripleWriters.uri.entity_prefixed(entity_id)

        output.write(f"{data_uri} a schema:Dataset .\n")
        output.write(f"{data_uri} schema:about {entity_uri} .\n")
        output.write(
            f"{data_uri} cc:license "
            "<http://creativecommons.org/publicdomain/zero/1.0/> .\n"
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
        output.write(f"{entity_uri} schema:sameAs <{wiki_url}> .\n")

    @staticmethod
    def write_direct_claim(
        output: TextIO, entity_id: str, property_id: str, value: str
    ):
        """Write direct claim triple: wd:Qxxx wdt:Pxxx value"""
        entity_uri = TripleWriters.uri.entity_prefixed(entity_id)
        output.write(f"{entity_uri} wdt:{property_id} {value} .\n")

    @staticmethod
    def write_statement(
        output: TextIO,
        entity_id: str,
        rdf_statement: "RDFStatement",
        shape: PropertyShape,
        property_registry,
        dedupe: HashDedupeBag | None = None,
    ):
        from models.rdf_builder.models.rdf_reference import RDFReference

        entity_uri = TripleWriters.uri.entity_prefixed(entity_id)
        stmt_uri_prefixed = TripleWriters.uri.statement_prefixed(rdf_statement.guid)

        # Link entity → statement
        output.write(
            f"{entity_uri} p:{rdf_statement.property_id} {stmt_uri_prefixed} .\n"
        )

        if rdf_statement.rank == "normal":
            output.write(
                f"{stmt_uri_prefixed} a wikibase:Statement, wikibase:BestRank .\n"
            )

            value = ValueFormatter.format_value(rdf_statement.value)
            TripleWriters.write_direct_claim(
                output, entity_id, rdf_statement.property_id, value
            )
        else:
            output.write(f"{stmt_uri_prefixed} a wikibase:Statement .\n")

        # Write statement value
        if TripleWriters._needs_value_node(rdf_statement.value):
            value_node_id = generate_value_node_uri(rdf_statement.value)

            output.write(
                f"{stmt_uri_prefixed} {shape.predicates.value_node} wdv:{value_node_id} .\n"
            )

            if rdf_statement.value.kind == "time":
                ValueNodeWriter.write_time_value_node(
                    output, value_node_id, rdf_statement.value, dedupe
                )
            elif rdf_statement.value.kind == "quantity":
                ValueNodeWriter.write_quantity_value_node(
                    output, value_node_id, rdf_statement.value, dedupe
                )
            elif rdf_statement.value.kind == "globe":
                ValueNodeWriter.write_globe_value_node(
                    output, value_node_id, rdf_statement.value, dedupe
                )
        else:
            value = ValueFormatter.format_value(rdf_statement.value)
            output.write(
                f"{stmt_uri_prefixed} {shape.predicates.statement} {value} .\n"
            )

        # Rank
        rank = (
            "NormalRank"
            if rdf_statement.rank == "normal"
            else (
                "PreferredRank"
                if rdf_statement.rank == "preferred"
                else "DeprecatedRank"
            )
        )
        output.write(f"{stmt_uri_prefixed} wikibase:rank wikibase:{rank} .\n")

        # Qualifiers
        for qual in rdf_statement.qualifiers:
            qv = ValueFormatter.format_value(qual.value)

            if TripleWriters._needs_value_node(qual.value):
                qualifier_node_id = generate_value_node_uri(qual.value)

                output.write(
                    f"{stmt_uri_prefixed} {shape.predicates.qualifier_value} wdv:{qualifier_node_id} .\n"
                )

                if qual.value.kind == "time":
                    ValueNodeWriter.write_time_value_node(
                        output, qualifier_node_id, qual.value, dedupe
                    )
                elif qual.value.kind == "quantity":
                    ValueNodeWriter.write_quantity_value_node(
                        output, qualifier_node_id, qual.value, dedupe
                    )
                elif qual.value.kind == "globe":
                    ValueNodeWriter.write_globe_value_node(
                        output, qualifier_node_id, qual.value, dedupe
                    )
            else:
                output.write(
                    f"{stmt_uri_prefixed} {shape.predicates.qualifier} {qv} .\n"
                )

        # References
        for ref in rdf_statement.references:
            rdf_ref = RDFReference(ref, stmt_uri_prefixed)
            ref_uri = rdf_ref.get_reference_uri()
            output.write(f"{stmt_uri_prefixed} prov:wasDerivedFrom {ref_uri} .\n")

            for snak in ref.snaks:
                snak_shape = property_registry.shape(snak.property)
                rv = ValueFormatter.format_value(snak.value)

                if TripleWriters._needs_value_node(snak.value):
                    ref_node_id = generate_value_node_uri(snak.value)

                    output.write(
                        f"{ref_uri} {snak_shape.predicates.reference_value} wdv:{ref_node_id} .\n"
                    )

                    if snak.value.kind == "time":
                        ValueNodeWriter.write_time_value_node(
                            output, ref_node_id, snak.value, dedupe
                        )
                    elif snak.value.kind == "quantity":
                        ValueNodeWriter.write_quantity_value_node(
                            output, ref_node_id, snak.value, dedupe
                        )
                    elif snak.value.kind == "globe":
                        ValueNodeWriter.write_globe_value_node(
                            output, ref_node_id, snak.value, dedupe
                        )
                else:
                    output.write(
                        f"{ref_uri} {snak_shape.predicates.reference} {rv} .\n"
                    )
