from typing import TextIO
from io import StringIO
from pydantic import BaseModel

from models.rdf_builder.property_registry.registry import PropertyRegistry
from models.rdf_builder.writers.triple import TripleWriters


class EntityToRdfConverter(BaseModel):
    properties: PropertyRegistry

    def convert_to_turtle(self, entity, output: TextIO):
        TripleWriters.write_entity_type(output, entity.id)
        TripleWriters.write_dataset_triples(output, entity.id)

        for lang, label in entity.labels.items():
            TripleWriters.write_label(output, entity.id, lang, label)

        for stmt in entity.statements:
            shape = self.properties.shape(stmt.property)
            TripleWriters.write_statement(
                output,
                entity.id,
                stmt,
                shape,
            )

    def convert_to_string(self, entity) -> str:
        buf = StringIO()
        self.convert_to_turtle(entity, buf)
        return buf.getvalue()
