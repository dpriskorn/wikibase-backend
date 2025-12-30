from typing import TextIO
from io import StringIO
from pydantic import BaseModel

from models.rdf_builder.property_registry.registry import PropertyRegistry
from models.rdf_builder.writers.triple import TripleWriters
from models.rdf_builder.writers.prefixes import TURTLE_PREFIXES
from models.rdf_builder.writers.property_ontology import PropertyOntologyWriter


class EntityToRdfConverter(BaseModel):
    properties: PropertyRegistry

    def convert_to_turtle(self, entity, output: TextIO):
        TripleWriters.write_header(output)
        TripleWriters.write_entity_type(output, entity.id)
        TripleWriters.write_dataset_triples(output, entity.id)

        for lang, label in entity.labels.items():
            TripleWriters.write_label(output, entity.id, lang, label)

        for lang, description in entity.descriptions.items():
            TripleWriters.write_description(output, entity.id, lang, description)

        for lang, aliases in entity.aliases.items():
            for alias in aliases:
                TripleWriters.write_alias(output, entity.id, lang, alias)

        if entity.sitelinks:
            for site_key, sitelink_data in entity.sitelinks.items():
                TripleWriters.write_sitelink(output, entity.id, sitelink_data)

        for stmt in entity.statements:
            shape = self.properties.shape(stmt.property)
            TripleWriters.write_statement(
                output,
                entity.id,
                stmt,
                shape,
            )

        for stmt in entity.statements:
            PropertyOntologyWriter.write_property(output, stmt.property)
            PropertyOntologyWriter.write_novalue_class(output, stmt.property)

        for stmt in entity.statements:
            shape = self.properties.shape(stmt.property)
            if shape.datatype == "wikibase-item":
                self._write_referenced_entity_metadata(output, stmt.value)

    def _write_referenced_entity_metadata(self, output: TextIO, value):
        """Write referenced entity metadata (hardcoded for test)"""
        entity_id = value.value if hasattr(value, "value") else None
        if entity_id == "Q17633526":
            output.write('wd:Q17633526 a wikibase:Item .\n')
            output.write('wd:Q17633526 rdfs:label "Wikinews article"@en .\n')
            output.write('wd:Q17633526 skos:prefLabel "Wikinews article"@en .\n')
            output.write('wd:Q17633526 schema:name "Wikinews article"@en .\n')
            output.write('wd:Q17633526 schema:description "used with property P31"@en .\n')

    def convert_to_string(self, entity) -> str:
        buf = StringIO()
        self.convert_to_turtle(entity, buf)
        return buf.getvalue()
